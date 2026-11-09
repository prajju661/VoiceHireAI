"""
Interview API routes for VoiceHire AI Adaptive Interview Engine.

Provides endpoints for interview lifecycle orchestration:
- POST   /api/interview/start
- POST   /api/interview/{session_id}/answer
- GET    /api/interview/{session_id}
- POST   /api/interview/{session_id}/complete
- GET    /api/interview
- DELETE /api/interview/{session_id}
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.models.interview import (
    DifficultyLevel,
    InterviewLanguage,
    InterviewQuestion,
    InterviewSummary,
    JobRole,
)
from app.services.interview_service import (
    InterviewServiceError,
    InterviewSessionManager,
    SessionCompletedError,
    SessionNotFoundError,
    SessionStateError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["Interview Engine"])


# =============================================================================
# Request / Response Schemas
# =============================================================================
class StartInterviewRequest(BaseModel):
    """Schema for initializing an adaptive interview session."""

    job_role: str = Field(
        default="Python Developer",
        description="Target job role (e.g. 'Python Developer', 'Data Analyst')",
    )
    language: InterviewLanguage = Field(
        default=InterviewLanguage.EN_IN,
        description="Interview language (en-IN, te-IN, te-en)",
    )
    initial_difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.INTERMEDIATE,
        description="Starting difficulty tier (beginner, intermediate, advanced)",
    )
    candidate_name: str | None = Field(
        default=None,
        description="Optional candidate display name",
    )
    candidate_email: str | None = Field(
        default=None,
        description="Optional candidate email address",
    )


class StartInterviewResponse(BaseModel):
    """Schema for interview initialization response."""

    session_id: str
    candidate_name: str | None = None
    candidate_email: str | None = None
    job_role: str
    language: str
    current_difficulty: str
    status: str
    reasoning_provider: str
    first_question: dict[str, Any]
    turn_number: int
    created_at: str


class SubmitAnswerRequest(BaseModel):
    """Schema for submitting candidate answer to the active question."""

    answer_text: str = Field(
        ...,
        description="Transcribed or written answer from the candidate",
    )


class SubmitAnswerResponse(BaseModel):
    """Schema for evaluation and next question response."""

    session_id: str
    turn_number: int
    score: float
    feedback: str
    strengths: list[str]
    improvement_areas: list[str]
    evidence_from_answer: list[str]
    next_question: dict[str, Any]
    updated_difficulty: str
    session_status: str


class SessionListResponse(BaseModel):
    """Schema for paginated session listing."""

    total: int
    limit: int
    offset: int
    sessions: list[dict[str, Any]]


class DeleteSessionResponse(BaseModel):
    """Schema for session deletion response."""

    success: bool
    message: str


# =============================================================================
# Dependency Injection
# =============================================================================
def get_interview_manager() -> InterviewSessionManager:
    """Provide an InterviewSessionManager instance."""
    return InterviewSessionManager()


# =============================================================================
# Routes
# =============================================================================
@router.post(
    "/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an adaptive interview session",
    description="Initializes a new interview session, persists it to SQLite, and returns the first question.",
)
def start_interview(
    request: StartInterviewRequest,
    manager: Annotated[InterviewSessionManager, Depends(get_interview_manager)],
) -> StartInterviewResponse:
    try:
        result = manager.start_interview(
            job_role=request.job_role,
            language=request.language,
            initial_difficulty=request.initial_difficulty,
            candidate_name=request.candidate_name,
            candidate_email=request.candidate_email,
        )
        return StartInterviewResponse(**result)
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.error("Unhandled error starting interview: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while starting the interview session.",
        ) from exc


@router.post(
    "/{session_id}/answer",
    response_model=SubmitAnswerResponse,
    summary="Submit candidate answer",
    description="Evaluates the candidate's answer to the active question, updates difficulty, and returns the next question.",
)
def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    manager: Annotated[InterviewSessionManager, Depends(get_interview_manager)],
) -> SubmitAnswerResponse:
    try:
        result = manager.submit_answer(
            session_id=session_id,
            answer_text=request.answer_text,
        )
        return SubmitAnswerResponse(**result)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except (SessionCompletedError, SessionStateError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.error("Unhandled error submitting answer for session %s: %s", session_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while evaluating the answer.",
        ) from exc


@router.get(
    "/{session_id}",
    summary="Get interview session details",
    description="Retrieves session status, difficulty, running scores, and all chronological turns.",
)
def get_session(
    session_id: str,
    manager: Annotated[InterviewSessionManager, Depends(get_interview_manager)],
) -> dict[str, Any]:
    try:
        return manager.get_session_details(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.error("Unhandled error retrieving session %s: %s", session_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving session details.",
        ) from exc


@router.post(
    "/{session_id}/complete",
    response_model=InterviewSummary,
    summary="Conclude interview and generate summary",
    description="Marks the interview as completed and generates the final performance evaluation report.",
)
def complete_interview(
    session_id: str,
    manager: Annotated[InterviewSessionManager, Depends(get_interview_manager)],
) -> InterviewSummary:
    try:
        return manager.complete_interview(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.error("Unhandled error completing session %s: %s", session_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while completing the interview session.",
        ) from exc


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List recent interview sessions",
    description="Returns a paginated list of interview sessions ordered by creation date.",
)
def list_sessions(
    manager: Annotated[InterviewSessionManager, Depends(get_interview_manager)],
    limit: Annotated[int, Query(ge=1, le=100, description="Max records to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Records offset")] = 0,
) -> SessionListResponse:
    try:
        result = manager.list_sessions(limit=limit, offset=offset)
        return SessionListResponse(**result)
    except Exception as exc:
        logger.error("Unhandled error listing sessions: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing interview sessions.",
        ) from exc


@router.delete(
    "/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Delete interview session",
    description="Deletes an interview session and all associated turns via cascading deletion.",
)
def delete_session(
    session_id: str,
    manager: Annotated[InterviewSessionManager, Depends(get_interview_manager)],
) -> DeleteSessionResponse:
    try:
        manager.delete_session(session_id)
        return DeleteSessionResponse(
            success=True,
            message=f"Interview session '{session_id}' and all associated turns deleted successfully.",
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.error("Unhandled error deleting session %s: %s", session_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the interview session.",
        ) from exc
