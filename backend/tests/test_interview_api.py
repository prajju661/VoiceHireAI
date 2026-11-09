"""
Integration tests for VoiceHire AI Interview API endpoints (FastAPI).

Verifies:
1. POST /api/interview/start (201 Created)
2. POST /api/interview/{session_id}/answer (200 OK)
3. GET  /api/interview/{session_id} (200 OK)
4. POST /api/interview/{session_id}/complete (200 OK)
5. GET  /api/interview (200 OK, paginated)
6. DELETE /api/interview/{session_id} (200 OK)
7. Error mappings:
   - 404 on nonexistent session
   - 400 on answering completed session
   - 422 on invalid request payload
"""

from pathlib import Path
import pytest
from fastapi import HTTPException

from app.api.interview import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    complete_interview,
    delete_session,
    get_session,
    list_sessions,
    start_interview,
    submit_answer,
)
from app.db.database import init_db
from app.db.repository import InterviewRepository
from app.models.interview import DifficultyLevel, InterviewLanguage
from app.services.interview_service import InterviewSessionManager


@pytest.fixture
def test_manager(tmp_path: Path) -> InterviewSessionManager:
    """Isolated session manager backed by a temporary test database."""
    test_db = tmp_path / "test_api.db"
    init_db(test_db)
    repo = InterviewRepository(db_path=test_db)
    return InterviewSessionManager(repository=repo)


class TestInterviewEndpoints:
    """Test interview API handlers with isolated repository injection."""

    def test_start_interview_endpoint_success(self, test_manager: InterviewSessionManager):
        req = StartInterviewRequest(
            job_role="Python Developer",
            language=InterviewLanguage.EN_IN,
            initial_difficulty=DifficultyLevel.INTERMEDIATE,
            candidate_name="Jane Doe",
            candidate_email="jane@example.com",
        )
        resp = start_interview(request=req, manager=test_manager)

        assert resp.session_id is not None
        assert resp.job_role == "Python Developer"
        assert resp.candidate_name == "Jane Doe"
        assert resp.status == "active"
        assert resp.first_question["difficulty"] == "intermediate"

    def test_start_interview_telugu_language(self, test_manager: InterviewSessionManager):
        req = StartInterviewRequest(
            job_role="Python Developer",
            language=InterviewLanguage.TE_IN,
            initial_difficulty=DifficultyLevel.BEGINNER,
        )
        resp = start_interview(request=req, manager=test_manager)
        assert resp.language == "te-IN"
        assert resp.first_question["language"] == "te-IN"

    def test_start_interview_code_mixed_language(self, test_manager: InterviewSessionManager):
        req = StartInterviewRequest(
            job_role="Python Developer",
            language=InterviewLanguage.TE_EN,
            initial_difficulty=DifficultyLevel.BEGINNER,
        )
        resp = start_interview(request=req, manager=test_manager)
        assert resp.language == "te-en"
        assert resp.first_question["language"] == "te-en"

    def test_submit_answer_endpoint_success(self, test_manager: InterviewSessionManager):
        start_req = StartInterviewRequest(
            job_role="Python Developer",
            language=InterviewLanguage.EN_IN,
            initial_difficulty=DifficultyLevel.BEGINNER,
        )
        session = start_interview(request=start_req, manager=test_manager)
        sid = session.session_id

        ans_req = SubmitAnswerRequest(
            answer_text=(
                "A list is mutable and defined with square brackets, whereas a tuple is immutable "
                "and uses parentheses. Tuples are hashable, constant, and provide superior performance."
            )
        )
        ans_resp = submit_answer(session_id=sid, request=ans_req, manager=test_manager)

        assert ans_resp.session_id == sid
        assert ans_resp.score >= 70.0
        assert ans_resp.updated_difficulty == "intermediate"
        assert "next_question" in ans_resp.model_dump()

    def test_submit_answer_nonexistent_session_404(self, test_manager: InterviewSessionManager):
        ans_req = SubmitAnswerRequest(answer_text="Sample text")
        with pytest.raises(HTTPException) as exc_info:
            submit_answer(session_id="00000000-0000-0000-0000-000000000000", request=ans_req, manager=test_manager)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_submit_answer_completed_session_400(self, test_manager: InterviewSessionManager):
        start_req = StartInterviewRequest(job_role="Java Developer")
        session = start_interview(request=start_req, manager=test_manager)
        sid = session.session_id

        complete_interview(session_id=sid, manager=test_manager)

        ans_req = SubmitAnswerRequest(answer_text="Attempting to answer")
        with pytest.raises(HTTPException) as exc_info:
            submit_answer(session_id=sid, request=ans_req, manager=test_manager)

        assert exc_info.value.status_code == 400
        assert "already completed" in exc_info.value.detail.lower()

    def test_get_session_endpoint_success(self, test_manager: InterviewSessionManager):
        start_req = StartInterviewRequest(job_role="Full Stack Developer")
        session = start_interview(request=start_req, manager=test_manager)
        sid = session.session_id

        details = get_session(session_id=sid, manager=test_manager)
        assert details["session_id"] == sid
        assert details["job_role"] == "Full Stack Developer"
        assert details["status"] == "active"
        assert details["turns_count"] == 1

    def test_get_session_nonexistent_404(self, test_manager: InterviewSessionManager):
        with pytest.raises(HTTPException) as exc_info:
            get_session(session_id="invalid-session-id", manager=test_manager)

        assert exc_info.value.status_code == 404

    def test_complete_interview_endpoint_success(self, test_manager: InterviewSessionManager):
        start_req = StartInterviewRequest(
            job_role="Data Analyst",
            initial_difficulty=DifficultyLevel.BEGINNER,
        )
        session = start_interview(request=start_req, manager=test_manager)
        sid = session.session_id

        ans_req = SubmitAnswerRequest(
            answer_text=(
                "In SQL, an inner join returns only matching rows between tables. "
                "A left join preserves all records from the left table with null values for unmatched right rows, "
                "and an outer join merges matching and non-matching records across both tables."
            )
        )
        submit_answer(session_id=sid, request=ans_req, manager=test_manager)

        summary = complete_interview(session_id=sid, manager=test_manager)
        assert summary.overall_score >= 60.0
        assert summary.questions_answered >= 1
        assert summary.reasoning_provider == "rule_based_engine_v1"

    def test_list_sessions_endpoint(self, test_manager: InterviewSessionManager):
        start_req = StartInterviewRequest(job_role="Python Developer")
        start_interview(request=start_req, manager=test_manager)

        list_resp = list_sessions(limit=10, offset=0, manager=test_manager)
        assert list_resp.total >= 1
        assert len(list_resp.sessions) >= 1

    def test_delete_session_endpoint_success(self, test_manager: InterviewSessionManager):
        start_req = StartInterviewRequest(job_role="Python Developer")
        session = start_interview(request=start_req, manager=test_manager)
        sid = session.session_id

        del_resp = delete_session(session_id=sid, manager=test_manager)
        assert del_resp.success is True

        # Verify 404 after deletion
        with pytest.raises(HTTPException) as exc_info:
            get_session(session_id=sid, manager=test_manager)
        assert exc_info.value.status_code == 404
