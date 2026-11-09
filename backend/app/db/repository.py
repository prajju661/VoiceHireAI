"""
Database repository for VoiceHire AI interview sessions and turns.

Encapsulates all SQL statements using parameterized queries, strictly
avoiding SQL concatenation or raw queries in route handlers.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any
import uuid

from app.core.config import settings
from app.db.database import get_connection
from app.models.interview import AnswerEvaluation, InterviewQuestion

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class InterviewRepository:
    """
    Data repository for managing SQLite persistence of interview sessions and turns.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.DATABASE_PATH

    # -------------------------------------------------------------------------
    # Sessions
    # -------------------------------------------------------------------------
    def create_session(
        self,
        job_role: str,
        language: str,
        difficulty: str,
        reasoning_provider: str,
        candidate_name: str | None = None,
        candidate_email: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new interview session record.
        """
        sid = session_id or str(uuid.uuid4())
        now = _utc_now_iso()

        sql = """
        INSERT INTO interview_sessions (
            id, candidate_name, candidate_email, job_role, language,
            difficulty, status, reasoning_provider, overall_score,
            created_at, updated_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, NULL, ?, ?, NULL);
        """
        with get_connection(self.db_path) as conn:
            conn.execute(
                sql,
                (
                    sid,
                    candidate_name,
                    candidate_email,
                    job_role,
                    language,
                    difficulty,
                    reasoning_provider,
                    now,
                    now,
                ),
            )

        return self.get_session(sid) or {}

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve a single interview session by its unique ID.
        """
        sql = "SELECT * FROM interview_sessions WHERE id = ?;"
        with get_connection(self.db_path) as conn:
            row = conn.execute(sql, (session_id,)).fetchone()
            if row is None:
                return None
            return dict(row)

    def update_session_difficulty(self, session_id: str, new_difficulty: str) -> None:
        """
        Update the current difficulty level of an active session.
        """
        sql = """
        UPDATE interview_sessions
        SET difficulty = ?, updated_at = ?
        WHERE id = ?;
        """
        now = _utc_now_iso()
        with get_connection(self.db_path) as conn:
            conn.execute(sql, (new_difficulty, now, session_id))

    def complete_session(self, session_id: str, overall_score: float) -> None:
        """
        Mark an interview session as completed with its final overall score.
        """
        now = _utc_now_iso()
        sql = """
        UPDATE interview_sessions
        SET status = 'completed', overall_score = ?, completed_at = ?, updated_at = ?
        WHERE id = ?;
        """
        with get_connection(self.db_path) as conn:
            conn.execute(sql, (overall_score, now, now, session_id))

    def list_sessions(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """
        List recent interview sessions sorted by creation time descending.
        """
        sql = """
        SELECT * FROM interview_sessions
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
        """
        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, (limit, offset)).fetchall()
            return [dict(r) for r in rows]

    def count_sessions(self) -> int:
        """
        Return the total count of interview sessions in the database.
        """
        sql = "SELECT COUNT(*) as cnt FROM interview_sessions;"
        with get_connection(self.db_path) as conn:
            row = conn.execute(sql).fetchone()
            return int(row["cnt"]) if row else 0

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its associated turns via cascading deletion.
        """
        sql = "DELETE FROM interview_sessions WHERE id = ?;"
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(sql, (session_id,))
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # Turns
    # -------------------------------------------------------------------------
    def save_turn_question(
        self,
        session_id: str,
        turn_number: int,
        question: InterviewQuestion,
    ) -> int:
        """
        Record a newly presented question as a pending turn in the session.
        """
        now = _utc_now_iso()
        sql = """
        INSERT INTO interview_turns (
            session_id, turn_number, question_id, question_text,
            question_category, question_difficulty, answer_text,
            score, feedback, strengths, improvement_areas,
            evidence_from_answer, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, '[]', '[]', '[]', ?);
        """
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                sql,
                (
                    session_id,
                    turn_number,
                    question.question_id,
                    question.question_text,
                    question.category,
                    question.difficulty.value if hasattr(question.difficulty, "value") else str(question.difficulty),
                    now,
                ),
            )
            return int(cursor.lastrowid or 0)

    def update_turn_answer_and_evaluation(
        self,
        turn_id: int,
        answer_text: str,
        evaluation: AnswerEvaluation,
    ) -> None:
        """
        Record candidate answer text and reasoning evaluation results for a turn.
        """
        sql = """
        UPDATE interview_turns
        SET answer_text = ?,
            score = ?,
            feedback = ?,
            strengths = ?,
            improvement_areas = ?,
            evidence_from_answer = ?
        WHERE id = ?;
        """
        with get_connection(self.db_path) as conn:
            conn.execute(
                sql,
                (
                    answer_text,
                    evaluation.score,
                    evaluation.feedback,
                    json.dumps(evaluation.strengths),
                    json.dumps(evaluation.improvement_areas),
                    json.dumps(evaluation.evidence_from_answer),
                    turn_id,
                ),
            )

    def get_session_turns(self, session_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all turns for a session in chronological order.
        """
        sql = """
        SELECT * FROM interview_turns
        WHERE session_id = ?
        ORDER BY turn_number ASC, id ASC;
        """
        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, (session_id,)).fetchall()
            results = []
            for r in rows:
                turn_dict = dict(r)
                # Parse JSON fields safely
                for field in ("strengths", "improvement_areas", "evidence_from_answer"):
                    val = turn_dict.get(field)
                    if isinstance(val, str):
                        try:
                            turn_dict[field] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            turn_dict[field] = []
                    elif val is None:
                        turn_dict[field] = []
                results.append(turn_dict)
            return results

    def get_latest_pending_turn(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve the latest turn for a session that has not yet received an answer.
        """
        sql = """
        SELECT * FROM interview_turns
        WHERE session_id = ? AND answer_text IS NULL
        ORDER BY turn_number DESC, id DESC
        LIMIT 1;
        """
        with get_connection(self.db_path) as conn:
            row = conn.execute(sql, (session_id,)).fetchone()
            if row is None:
                return None
            turn_dict = dict(row)
            for field in ("strengths", "improvement_areas", "evidence_from_answer"):
                turn_dict[field] = []
            return turn_dict
