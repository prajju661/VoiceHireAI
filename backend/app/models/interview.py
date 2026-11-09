"""
Domain models and schemas for VoiceHire AI Adaptive Interview Engine.

Defines validated data structures for interview sessions, questions,
answer evaluations, difficulty levels, and performance summaries.
"""

from enum import Enum
from typing import Annotated
from pydantic import BaseModel, Field, field_validator


class DifficultyLevel(str, Enum):
    """Interview question and candidate assessment difficulty tiers."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class InterviewLanguage(str, Enum):
    """Supported interview languages and conversational modes."""

    EN_IN = "en-IN"  # Indian English
    TE_IN = "te-IN"  # Telugu script
    TE_EN = "te-en"  # Telugu-English code-mixed (Tanglish)


class JobRole(str, Enum):
    """Pre-configured target technical roles."""

    PYTHON_DEVELOPER = "Python Developer"
    JAVA_DEVELOPER = "Java Developer"
    FULL_STACK_DEVELOPER = "Full Stack Developer"
    DATA_ANALYST = "Data Analyst"


class InterviewQuestion(BaseModel):
    """A technical interview question presented to the candidate."""

    question_id: str = Field(..., min_length=1, description="Unique question identifier")
    question_text: str = Field(..., min_length=5, description="Full question text prompt")
    role: str = Field(..., description="Target job role")
    category: str = Field(..., min_length=2, description="Technical category or topic")
    difficulty: DifficultyLevel = Field(..., description="Target difficulty level")
    language: InterviewLanguage = Field(
        default=InterviewLanguage.EN_IN,
        description="Language or code-mix mode of the question",
    )
    expected_concepts: list[str] = Field(
        default_factory=list,
        description="Key concepts or technical keywords expected in a strong answer",
    )


class AnswerEvaluation(BaseModel):
    """
    Transparent, evidence-based evaluation of a candidate's answer.

    Contains scores, extracted textual evidence, identified strengths,
    and constructively framed missing concepts without extrapolating
    unsupported personal traits or permanent ability limits.
    """

    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Numeric score between 0.0 and 100.0 based on answer completeness and relevance",
    )
    is_relevant: bool = Field(
        True,
        description="Whether the answer addressed the core topic of the question",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Specific technical strengths demonstrated in this response",
    )
    improvement_areas: list[str] = Field(
        default_factory=list,
        description="Specific concepts not mentioned or areas for technical elaboration",
    )
    feedback: str = Field(
        ...,
        min_length=5,
        description="Constructive, transparent feedback explaining the score",
    )
    evidence_from_answer: list[str] = Field(
        default_factory=list,
        description="Direct quotes or extracted phrases from the answer used as scoring evidence",
    )
    recommended_difficulty: DifficultyLevel = Field(
        ...,
        description="Difficulty level recommended for the subsequent question",
    )
    identified_concepts: list[str] = Field(
        default_factory=list,
        description="Technical concepts verified to be present in this response",
    )
    missing_concepts: list[str] = Field(
        default_factory=list,
        description="Expected concepts that were absent in this specific response",
    )

    @field_validator("score")
    @classmethod
    def validate_score_bounds(cls, v: float) -> float:
        if v < 0.0 or v > 100.0:
            raise ValueError("Score must be between 0.0 and 100.0 inclusive")
        return round(v, 1)


class InterviewTurn(BaseModel):
    """A single question-and-answer exchange in an interview session."""

    turn_number: int = Field(..., ge=1, description="Sequential turn index")
    question: InterviewQuestion = Field(..., description="Question asked")
    candidate_answer: str = Field(..., description="Transcribed candidate answer")
    evaluation: AnswerEvaluation = Field(..., description="Evaluation of the answer")


class InterviewSummary(BaseModel):
    """
    Final structured performance report for a completed interview session.
    """

    overall_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Aggregate score across all evaluated interview questions (0-100)",
    )
    category_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Average score broken down by technical category",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Summary of demonstrated technical proficiencies grounded in answer evidence",
    )
    improvement_areas: list[str] = Field(
        default_factory=list,
        description="Topics where the candidate did not cover key technical concepts",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable study and practice recommendations",
    )
    questions_answered: int = Field(
        ...,
        ge=0,
        description="Total number of evaluated questions in the session",
    )
    reasoning_provider: str = Field(
        ...,
        description="Identifier of the reasoning engine that performed evaluation (e.g. rule_based_fallback_v1)",
    )
    final_difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.INTERMEDIATE,
        description="Highest or final difficulty reached during the adaptive interview",
    )

    @field_validator("overall_score")
    @classmethod
    def validate_overall_score(cls, v: float) -> float:
        if v < 0.0 or v > 100.0:
            raise ValueError("Overall score must be between 0.0 and 100.0 inclusive")
        return round(v, 1)
