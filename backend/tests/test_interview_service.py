"""
Unit tests for VoiceHire AI InterviewSessionManager (Service layer).

Verifies:
1. Starting an interview with initial question and turn persistence.
2. Submitting answers, difficulty updates, and follow-up question generation.
3. Preventing answers to nonexistent sessions (SessionNotFoundError).
4. Preventing answers to completed sessions (SessionCompletedError).
5. Retrieving comprehensive session details.
6. Completing interviews with final summaries.
7. Listing and deleting interview sessions.
"""

from pathlib import Path
import pytest

from app.db.database import init_db
from app.db.repository import InterviewRepository
from app.models.interview import DifficultyLevel, InterviewLanguage
from app.services.interview_service import (
    InterviewSessionManager,
    SessionCompletedError,
    SessionNotFoundError,
)


@pytest.fixture
def service_manager(tmp_path: Path) -> InterviewSessionManager:
    """Provide an InterviewSessionManager configured with an isolated test SQLite DB."""
    db_file = tmp_path / "test_service.db"
    init_db(db_file)
    repo = InterviewRepository(db_path=db_file)
    return InterviewSessionManager(repository=repo)


class TestInterviewSessionManagerLifecycle:
    """Verify end-to-end interview turn loop."""

    def test_start_interview_creates_turn_1(self, service_manager: InterviewSessionManager):
        res = service_manager.start_interview(
            job_role="Python Developer",
            language=InterviewLanguage.EN_IN,
            initial_difficulty=DifficultyLevel.BEGINNER,
            candidate_name="Bob Developer",
        )

        assert res["session_id"] is not None
        assert res["job_role"] == "Python Developer"
        assert res["status"] == "active"
        assert res["turn_number"] == 1
        assert "first_question" in res
        assert res["first_question"]["difficulty"] == "beginner"

    def test_submit_answer_and_receive_follow_up(self, service_manager: InterviewSessionManager):
        started = service_manager.start_interview(
            job_role="Python Developer",
            language=InterviewLanguage.EN_IN,
            initial_difficulty=DifficultyLevel.BEGINNER,
        )
        sid = started["session_id"]

        answer = (
            "A list is mutable and defined with square brackets, whereas a tuple is immutable "
            "and defined with parentheses. Tuples are hashable and constant, offering better performance."
        )
        ans_res = service_manager.submit_answer(session_id=sid, answer_text=answer)

        assert ans_res["session_id"] == sid
        assert ans_res["score"] >= 70.0
        assert ans_res["updated_difficulty"] == "intermediate"
        assert "next_question" in ans_res
        assert ans_res["next_question"]["difficulty"] == "intermediate"

        # Check session details
        details = service_manager.get_session_details(sid)
        assert details["turns_count"] == 2  # Turn 1 (answered) + Turn 2 (pending)
        assert details["overall_score"] >= 70.0

    def test_submit_answer_nonexistent_session_raises_404(self, service_manager: InterviewSessionManager):
        with pytest.raises(SessionNotFoundError):
            service_manager.submit_answer("nonexistent-uuid", "Some answer")

    def test_submit_answer_completed_session_raises_400(self, service_manager: InterviewSessionManager):
        started = service_manager.start_interview(
            job_role="Python Developer",
            language=InterviewLanguage.EN_IN,
            initial_difficulty=DifficultyLevel.BEGINNER,
        )
        sid = started["session_id"]

        # Complete session
        service_manager.complete_interview(sid)

        # Attempt to answer
        with pytest.raises(SessionCompletedError):
            service_manager.submit_answer(sid, "Answer after completion")

    def test_complete_interview_returns_summary(self, service_manager: InterviewSessionManager):
        started = service_manager.start_interview(
            job_role="Java Developer",
            language=InterviewLanguage.EN_IN,
            initial_difficulty=DifficultyLevel.BEGINNER,
        )
        sid = started["session_id"]

        service_manager.submit_answer(
            sid,
            "The four core principles of OOP are encapsulation, inheritance, polymorphism, and abstraction. "
            "In Java, encapsulation binds state, inheritance extends a base class, polymorphism allows override, "
            "and abstraction is implemented via interface and abstract classes.",
        )

        summary = service_manager.complete_interview(sid)
        assert summary.overall_score >= 70.0
        assert summary.questions_answered >= 1
        assert len(summary.strengths) > 0
        assert summary.reasoning_provider == "rule_based_engine_v1"

        details = service_manager.get_session_details(sid)
        assert details["status"] == "completed"

    def test_delete_session(self, service_manager: InterviewSessionManager):
        started = service_manager.start_interview(
            job_role="Data Analyst",
            language=InterviewLanguage.EN_IN,
        )
        sid = started["session_id"]
        assert service_manager.delete_session(sid) is True

        with pytest.raises(SessionNotFoundError):
            service_manager.get_session_details(sid)
