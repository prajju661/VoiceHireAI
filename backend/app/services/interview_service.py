"""
Interview session service for VoiceHire AI Adaptive Interview Engine.

Orchestrates the interview lifecycle, coordinating database persistence
(InterviewRepository) with the reasoning provider (BaseReasoningProvider).
"""

from typing import Any
import logging

from app.db.repository import InterviewRepository
from app.models.interview import (
    AnswerEvaluation,
    DifficultyLevel,
    InterviewLanguage,
    InterviewQuestion,
    InterviewSummary,
    InterviewTurn,
)
from app.services.reasoning.base import BaseReasoningProvider
from app.services.reasoning.rule_based import RuleBasedReasoner

logger = logging.getLogger(__name__)


# =============================================================================
# Domain Exceptions
# =============================================================================
class InterviewServiceError(Exception):
    """Base exception for interview orchestration errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SessionNotFoundError(InterviewServiceError):
    """Raised when an interview session ID is not found."""

    def __init__(self, message: str = "Interview session not found.") -> None:
        super().__init__(message, status_code=404)


class SessionCompletedError(InterviewServiceError):
    """Raised when attempting to submit an answer to an already completed interview."""

    def __init__(self, message: str = "Cannot submit an answer to a completed interview session.") -> None:
        super().__init__(message, status_code=400)


class SessionStateError(InterviewServiceError):
    """Raised when session state is inconsistent or cannot accept an answer."""

    def __init__(self, message: str = "Interview session state is invalid.") -> None:
        super().__init__(message, status_code=400)


# =============================================================================
# InterviewSessionManager
# =============================================================================
class InterviewSessionManager:
    """
    Coordinates stateful interview workflows across SQLite storage and reasoning engines.
    """

    def __init__(
        self,
        repository: InterviewRepository | None = None,
        reasoning_provider: BaseReasoningProvider | None = None,
    ) -> None:
        self.repository = repository or InterviewRepository()
        self.reasoning_provider = reasoning_provider or RuleBasedReasoner()

    def start_interview(
        self,
        job_role: str,
        language: InterviewLanguage = InterviewLanguage.EN_IN,
        initial_difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
        candidate_name: str | None = None,
        candidate_email: str | None = None,
    ) -> dict[str, Any]:
        """
        Start a new interview session and persist its initial question.
        """
        # 1. Generate initial question via reasoning provider
        initial_question = self.reasoning_provider.generate_initial_question(
            role=job_role,
            language=language,
            difficulty=initial_difficulty,
        )

        # 2. Persist session record
        session = self.repository.create_session(
            job_role=job_role,
            language=language.value if hasattr(language, "value") else str(language),
            difficulty=initial_difficulty.value if hasattr(initial_difficulty, "value") else str(initial_difficulty),
            reasoning_provider=self.reasoning_provider.provider_name,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
        )

        session_id = session["id"]

        # 3. Persist first question as turn 1
        self.repository.save_turn_question(
            session_id=session_id,
            turn_number=1,
            question=initial_question,
        )

        logger.info(
            "Started interview session %s for role '%s' [%s, %s]",
            session_id, job_role, language.value, initial_difficulty.value
        )

        return {
            "session_id": session_id,
            "candidate_name": session.get("candidate_name"),
            "candidate_email": session.get("candidate_email"),
            "job_role": session["job_role"],
            "language": session["language"],
            "current_difficulty": session["difficulty"],
            "status": session["status"],
            "reasoning_provider": session["reasoning_provider"],
            "first_question": initial_question.model_dump(),
            "turn_number": 1,
            "created_at": session["created_at"],
        }

    def submit_answer(
        self,
        session_id: str,
        answer_text: str,
    ) -> dict[str, Any]:
        """
        Evaluate candidate's answer for the active question, record evaluation,
        update session difficulty, and generate a follow-up question.
        """
        # 1. Retrieve session
        session = self.repository.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Interview session '{session_id}' not found.")

        if session["status"] == "completed":
            raise SessionCompletedError(
                f"Interview session '{session_id}' is already completed. Answers cannot be submitted."
            )

        # 2. Retrieve pending turn
        pending_turn = self.repository.get_latest_pending_turn(session_id)
        if not pending_turn:
            raise SessionStateError(
                f"No question is currently awaiting an answer in session '{session_id}'."
            )

        # 3. Reconstruct question with expected concepts from provider question bank if available
        current_question = self._resolve_question(
            question_id=pending_turn["question_id"],
            fallback_text=pending_turn["question_text"],
            fallback_category=pending_turn["question_category"],
            fallback_difficulty=DifficultyLevel(pending_turn["question_difficulty"]),
            role=session["job_role"],
            language=InterviewLanguage(session["language"]),
        )

        # 4. Evaluate answer via reasoning provider
        current_diff = DifficultyLevel(session["difficulty"])
        evaluation: AnswerEvaluation = self.reasoning_provider.evaluate_answer(
            question=current_question,
            answer_text=answer_text,
            current_difficulty=current_diff,
        )

        # 5. Persist answer and evaluation for this turn
        self.repository.update_turn_answer_and_evaluation(
            turn_id=pending_turn["id"],
            answer_text=answer_text,
            evaluation=evaluation,
        )

        # 6. Update session difficulty in DB
        next_difficulty = evaluation.recommended_difficulty
        self.repository.update_session_difficulty(
            session_id=session_id,
            new_difficulty=next_difficulty.value,
        )

        # 7. Collect asked question IDs to prevent duplicates
        all_turns = self.repository.get_session_turns(session_id)
        asked_ids = {t["question_id"] for t in all_turns}

        # 8. Generate follow-up question
        next_question: InterviewQuestion = self.reasoning_provider.generate_follow_up_question(
            role=session["job_role"],
            previous_question=current_question,
            evaluation=evaluation,
            asked_question_ids=asked_ids,
            language=InterviewLanguage(session["language"]),
        )

        # 9. Persist next question as a pending turn
        next_turn_number = len(all_turns) + 1
        self.repository.save_turn_question(
            session_id=session_id,
            turn_number=next_turn_number,
            question=next_question,
        )

        logger.info(
            "Session %s turn %d evaluated (score: %.1f, diff: %s -> %s)",
            session_id, pending_turn["turn_number"], evaluation.score,
            current_diff.value, next_difficulty.value
        )

        return {
            "session_id": session_id,
            "turn_number": pending_turn["turn_number"],
            "evaluation": evaluation.model_dump(),
            "score": evaluation.score,
            "feedback": evaluation.feedback,
            "strengths": evaluation.strengths,
            "improvement_areas": evaluation.improvement_areas,
            "evidence_from_answer": evaluation.evidence_from_answer,
            "next_question": next_question.model_dump(),
            "updated_difficulty": next_difficulty.value,
            "session_status": "active",
        }

    def get_session_details(self, session_id: str) -> dict[str, Any]:
        """
        Retrieve comprehensive session details, turns, running scores, and state.
        """
        session = self.repository.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Interview session '{session_id}' not found.")

        turns = self.repository.get_session_turns(session_id)

        # Compute running score from answered turns
        answered_scores = [t["score"] for t in turns if t["score"] is not None]
        current_score = (
            round(sum(answered_scores) / len(answered_scores), 1)
            if answered_scores
            else None
        )

        return {
            "session_id": session["id"],
            "candidate_name": session.get("candidate_name"),
            "candidate_email": session.get("candidate_email"),
            "job_role": session["job_role"],
            "language": session["language"],
            "current_difficulty": session["difficulty"],
            "status": session["status"],
            "reasoning_provider": session["reasoning_provider"],
            "overall_score": session.get("overall_score") or current_score,
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "completed_at": session.get("completed_at"),
            "turns_count": len(turns),
            "turns": turns,
        }

    def complete_interview(self, session_id: str) -> InterviewSummary:
        """
        Conclude the interview session, generate aggregate summary report,
        and update session status to 'completed'.
        """
        session = self.repository.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Interview session '{session_id}' not found.")

        raw_turns = self.repository.get_session_turns(session_id)

        # Convert answered turns to typed InterviewTurn list
        completed_turns: list[InterviewTurn] = []
        for t in raw_turns:
            if t["answer_text"] is not None and t["score"] is not None:
                q = self._resolve_question(
                    question_id=t["question_id"],
                    fallback_text=t["question_text"],
                    fallback_category=t["question_category"],
                    fallback_difficulty=DifficultyLevel(t["question_difficulty"]),
                    role=session["job_role"],
                    language=InterviewLanguage(session["language"]),
                )
                ev = AnswerEvaluation(
                    score=float(t["score"]),
                    is_relevant=True,
                    strengths=t.get("strengths", []),
                    improvement_areas=t.get("improvement_areas", []),
                    feedback=t.get("feedback", ""),
                    evidence_from_answer=t.get("evidence_from_answer", []),
                    recommended_difficulty=DifficultyLevel(session["difficulty"]),
                )
                completed_turns.append(
                    InterviewTurn(
                        turn_number=t["turn_number"],
                        question=q,
                        candidate_answer=t["answer_text"],
                        evaluation=ev,
                    )
                )

        # Generate summary via reasoning provider
        summary = self.reasoning_provider.generate_final_summary(
            role=session["job_role"],
            turns=completed_turns,
        )

        # Persist completed status and final overall score
        self.repository.complete_session(session_id, overall_score=summary.overall_score)

        logger.info(
            "Completed session %s: %d questions answered, overall score: %.1f",
            session_id, len(completed_turns), summary.overall_score
        )

        return summary

    def list_sessions(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """
        List recent interview sessions with total count and pagination metadata.
        """
        sessions = self.repository.list_sessions(limit=limit, offset=offset)
        total = self.repository.count_sessions()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "sessions": sessions,
        }

    def delete_session(self, session_id: str) -> bool:
        """
        Delete an interview session and its cascading child turns.
        """
        session = self.repository.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Interview session '{session_id}' not found.")
        return self.repository.delete_session(session_id)

    # -------------------------------------------------------------------------
    # Helper: Resolve full question from provider bank
    # -------------------------------------------------------------------------
    def _resolve_question(
        self,
        question_id: str,
        fallback_text: str,
        fallback_category: str,
        fallback_difficulty: DifficultyLevel,
        role: str,
        language: InterviewLanguage,
    ) -> InterviewQuestion:
        """
        Look up question in reasoning provider's internal bank if available to retain
        expected_concepts; otherwise build from database fields.
        """
        if hasattr(self.reasoning_provider, "_questions"):
            for q in self.reasoning_provider._questions:
                if q.question_id == question_id:
                    return q

        return InterviewQuestion(
            question_id=question_id,
            question_text=fallback_text,
            role=role,
            category=fallback_category,
            difficulty=fallback_difficulty,
            language=language,
            expected_concepts=[],
        )
