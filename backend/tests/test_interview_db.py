"""
Unit tests for VoiceHire AI SQLite database operations and repository layer.

Verifies:
1. Schema initialization and table creation.
2. Foreign key enforcement and cascading deletion.
3. Session persistence and retrieval.
4. Turn insertion, updates, and chronological ordering.
5. Persistence across database connection closing (simulated restarts).
6. Parameterized SQL and resistance to SQL injection.
"""

from pathlib import Path
import pytest

from app.db.database import get_connection, init_db
from app.db.repository import InterviewRepository
from app.models.interview import (
    AnswerEvaluation,
    DifficultyLevel,
    InterviewLanguage,
    InterviewQuestion,
)


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Provide a temporary SQLite database path for isolated testing."""
    db_file = tmp_path / "test_voicehire.db"
    init_db(db_file)
    return db_file


@pytest.fixture
def repo(test_db_path: Path) -> InterviewRepository:
    """Provide a repository instance bound to the test database."""
    return InterviewRepository(db_path=test_db_path)


class TestDatabaseInitialization:
    """Verify table creation, schemas, and PRAGMA settings."""

    def test_tables_and_indexes_created(self, test_db_path: Path):
        with get_connection(test_db_path) as conn:
            # Verify tables exist
            tables = [
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';"
                ).fetchall()
            ]
            assert "interview_sessions" in tables
            assert "interview_turns" in tables

            # Verify foreign keys pragma is active
            fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            assert fk == 1

            # Verify indexes exist
            indexes = [
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index';"
                ).fetchall()
            ]
            assert "idx_turns_session_id" in indexes
            assert "idx_sessions_status" in indexes


class TestSessionRepository:
    """Verify session CRUD, difficulty updates, and persistence."""

    def test_create_and_retrieve_session(self, repo: InterviewRepository):
        session = repo.create_session(
            job_role="Python Developer",
            language="en-IN",
            difficulty="intermediate",
            reasoning_provider="rule_based_engine_v1",
            candidate_name="Alice Candidate",
            candidate_email="alice@example.com",
        )
        assert session["id"] is not None
        assert session["job_role"] == "Python Developer"
        assert session["candidate_name"] == "Alice Candidate"
        assert session["status"] == "active"
        assert session["difficulty"] == "intermediate"

        fetched = repo.get_session(session["id"])
        assert fetched is not None
        assert fetched["id"] == session["id"]
        assert fetched["job_role"] == "Python Developer"

    def test_update_session_difficulty(self, repo: InterviewRepository):
        session = repo.create_session(
            job_role="Java Developer",
            language="en-IN",
            difficulty="beginner",
            reasoning_provider="rule_based_engine_v1",
        )
        repo.update_session_difficulty(session["id"], "advanced")
        updated = repo.get_session(session["id"])
        assert updated is not None
        assert updated["difficulty"] == "advanced"

    def test_complete_session(self, repo: InterviewRepository):
        session = repo.create_session(
            job_role="Data Analyst",
            language="te-IN",
            difficulty="intermediate",
            reasoning_provider="rule_based_engine_v1",
        )
        repo.complete_session(session["id"], overall_score=88.5)
        completed = repo.get_session(session["id"])
        assert completed is not None
        assert completed["status"] == "completed"
        assert completed["overall_score"] == 88.5
        assert completed["completed_at"] is not None

    def test_list_and_count_sessions(self, repo: InterviewRepository):
        repo.create_session("Python Developer", "en-IN", "beginner", "test")
        repo.create_session("Java Developer", "en-IN", "intermediate", "test")
        assert repo.count_sessions() >= 2
        sessions = repo.list_sessions(limit=10, offset=0)
        assert len(sessions) >= 2

    def test_persistence_across_connection_restarts(self, test_db_path: Path):
        # Open and write via one repository instance
        repo1 = InterviewRepository(db_path=test_db_path)
        s = repo1.create_session("Python Developer", "en-IN", "advanced", "rule_based_engine_v1")
        sid = s["id"]

        # Simulate complete restart: instantiate a new repository with the same file
        repo2 = InterviewRepository(db_path=test_db_path)
        fetched = repo2.get_session(sid)
        assert fetched is not None
        assert fetched["id"] == sid
        assert fetched["difficulty"] == "advanced"


class TestTurnRepositoryAndCascadingDeletion:
    """Verify turn lifecycle and cascading foreign key behavior."""

    def test_save_and_update_turn(self, repo: InterviewRepository):
        session = repo.create_session("Python Developer", "en-IN", "beginner", "test")
        sid = session["id"]

        q = InterviewQuestion(
            question_id="py_test_01",
            question_text="What is a Python tuple?",
            role="Python Developer",
            category="Data Structures",
            difficulty=DifficultyLevel.BEGINNER,
        )

        turn_id = repo.save_turn_question(session_id=sid, turn_number=1, question=q)
        assert turn_id > 0

        pending = repo.get_latest_pending_turn(sid)
        assert pending is not None
        assert pending["turn_number"] == 1
        assert pending["question_id"] == "py_test_01"
        assert pending["answer_text"] is None

        ev = AnswerEvaluation(
            score=80.0,
            is_relevant=True,
            strengths=["Explained immutability"],
            improvement_areas=["Mention memory savings"],
            feedback="Good answer",
            evidence_from_answer=["tuples are immutable"],
            recommended_difficulty=DifficultyLevel.INTERMEDIATE,
        )

        repo.update_turn_answer_and_evaluation(
            turn_id=turn_id,
            answer_text="Tuples are immutable sequences.",
            evaluation=ev,
        )

        turns = repo.get_session_turns(sid)
        assert len(turns) == 1
        assert turns[0]["answer_text"] == "Tuples are immutable sequences."
        assert turns[0]["score"] == 80.0
        assert turns[0]["strengths"] == ["Explained immutability"]

        # Now no pending turn remains
        assert repo.get_latest_pending_turn(sid) is None

    def test_cascading_deletion_removes_child_turns(self, repo: InterviewRepository, test_db_path: Path):
        session = repo.create_session("Python Developer", "en-IN", "beginner", "test")
        sid = session["id"]

        q = InterviewQuestion(
            question_id="q1",
            question_text="Sample question",
            role="Python Developer",
            category="General",
            difficulty=DifficultyLevel.BEGINNER,
        )
        repo.save_turn_question(sid, 1, q)

        # Confirm turn exists
        turns_before = repo.get_session_turns(sid)
        assert len(turns_before) == 1

        # Delete session
        deleted = repo.delete_session(sid)
        assert deleted is True

        # Confirm session is gone
        assert repo.get_session(sid) is None

        # Verify turns table has 0 rows for this session via direct SQL
        with get_connection(test_db_path) as conn:
            remaining_turns = conn.execute(
                "SELECT COUNT(*) as cnt FROM interview_turns WHERE session_id = ?;", (sid,)
            ).fetchone()["cnt"]
            assert remaining_turns == 0


class TestSQLInjectionResistance:
    """Verify parameterized queries prevent SQL injection."""

    def test_malicious_input_stored_safely_as_literal_text(self, repo: InterviewRepository):
        injection_role = "'; DROP TABLE interview_sessions; --"
        injection_name = "' OR '1'='1"

        session = repo.create_session(
            job_role=injection_role,
            language="en-IN",
            difficulty="beginner",
            reasoning_provider="test",
            candidate_name=injection_name,
        )

        assert session["job_role"] == injection_role
        assert session["candidate_name"] == injection_name

        # Verify table still exists and data was safely stored
        fetched = repo.get_session(session["id"])
        assert fetched is not None
        assert fetched["job_role"] == injection_role
