"""
Unit tests for VoiceHire AI adaptive interview data models and schemas.

Tests:
1. DifficultyLevel and InterviewLanguage enum values.
2. Valid InterviewQuestion creation and field validation.
3. AnswerEvaluation score boundary validation (0.0 to 100.0).
4. Out-of-bounds score rejection (<0.0 or >100.0).
5. InterviewTurn structure and sequential turn number validation.
6. InterviewSummary schema and overall_score boundary validation.
"""

import pytest
from pydantic import ValidationError

from app.models.interview import (
    AnswerEvaluation,
    DifficultyLevel,
    InterviewLanguage,
    InterviewQuestion,
    InterviewSummary,
    InterviewTurn,
    JobRole,
)


class TestInterviewEnums:
    """Verify enum invariants and serialization values."""

    def test_difficulty_levels(self):
        assert DifficultyLevel.BEGINNER == "beginner"
        assert DifficultyLevel.INTERMEDIATE == "intermediate"
        assert DifficultyLevel.ADVANCED == "advanced"

    def test_interview_languages(self):
        assert InterviewLanguage.EN_IN == "en-IN"
        assert InterviewLanguage.TE_IN == "te-IN"
        assert InterviewLanguage.TE_EN == "te-en"

    def test_job_roles(self):
        assert JobRole.PYTHON_DEVELOPER == "Python Developer"
        assert JobRole.JAVA_DEVELOPER == "Java Developer"
        assert JobRole.FULL_STACK_DEVELOPER == "Full Stack Developer"
        assert JobRole.DATA_ANALYST == "Data Analyst"


class TestInterviewQuestionModel:
    """Verify InterviewQuestion data validation."""

    def test_valid_question(self):
        q = InterviewQuestion(
            question_id="py_01",
            question_text="Explain Python list vs tuple differences.",
            role="Python Developer",
            category="Data Structures",
            difficulty=DifficultyLevel.BEGINNER,
            language=InterviewLanguage.EN_IN,
            expected_concepts=["mutable", "immutable"],
        )
        assert q.question_id == "py_01"
        assert q.difficulty == DifficultyLevel.BEGINNER
        assert len(q.expected_concepts) == 2

    def test_invalid_short_question_text(self):
        with pytest.raises(ValidationError):
            InterviewQuestion(
                question_id="py_01",
                question_text="Hi",  # min_length=5
                role="Python Developer",
                category="General",
                difficulty=DifficultyLevel.BEGINNER,
            )

    def test_invalid_difficulty_enum(self):
        with pytest.raises(ValidationError):
            InterviewQuestion(
                question_id="py_01",
                question_text="Explain Python memory management.",
                role="Python Developer",
                category="General",
                difficulty="super_hard",  # invalid
            )


class TestAnswerEvaluationModel:
    """Verify AnswerEvaluation score validation and boundaries."""

    def test_valid_evaluation(self):
        ev = AnswerEvaluation(
            score=85.5,
            is_relevant=True,
            strengths=["Clear explanation of immutability."],
            improvement_areas=["Could mention memory usage."],
            feedback="Strong answer covering core differences.",
            evidence_from_answer=["tuples are immutable"],
            recommended_difficulty=DifficultyLevel.ADVANCED,
            identified_concepts=["immutable"],
            missing_concepts=["memory"],
        )
        assert ev.score == 85.5
        assert ev.is_relevant is True
        assert ev.recommended_difficulty == DifficultyLevel.ADVANCED

    def test_score_boundary_zero(self):
        ev = AnswerEvaluation(
            score=0.0,
            feedback="No answer provided.",
            recommended_difficulty=DifficultyLevel.BEGINNER,
        )
        assert ev.score == 0.0

    def test_score_boundary_one_hundred(self):
        ev = AnswerEvaluation(
            score=100.0,
            feedback="Exemplary answer.",
            recommended_difficulty=DifficultyLevel.ADVANCED,
        )
        assert ev.score == 100.0

    def test_score_negative_rejected(self):
        with pytest.raises(ValidationError):
            AnswerEvaluation(
                score=-5.0,
                feedback="Invalid score.",
                recommended_difficulty=DifficultyLevel.BEGINNER,
            )

    def test_score_exceeding_hundred_rejected(self):
        with pytest.raises(ValidationError):
            AnswerEvaluation(
                score=105.0,
                feedback="Invalid score.",
                recommended_difficulty=DifficultyLevel.ADVANCED,
            )


class TestInterviewTurnAndSummary:
    """Verify InterviewTurn and InterviewSummary reporting schemas."""

    def test_valid_turn(self):
        q = InterviewQuestion(
            question_id="q1",
            question_text="What is a Python decorator?",
            role="Python Developer",
            category="Advanced Features",
            difficulty=DifficultyLevel.INTERMEDIATE,
        )
        ev = AnswerEvaluation(
            score=70.0,
            feedback="Good explanation.",
            recommended_difficulty=DifficultyLevel.INTERMEDIATE,
        )
        turn = InterviewTurn(
            turn_number=1,
            question=q,
            candidate_answer="A decorator wraps a function to extend behavior.",
            evaluation=ev,
        )
        assert turn.turn_number == 1
        assert turn.question.question_id == "q1"

    def test_invalid_turn_number(self):
        q = InterviewQuestion(
            question_id="q1",
            question_text="What is a Python decorator?",
            role="Python Developer",
            category="Advanced Features",
            difficulty=DifficultyLevel.INTERMEDIATE,
        )
        ev = AnswerEvaluation(
            score=70.0,
            feedback="Good.",
            recommended_difficulty=DifficultyLevel.INTERMEDIATE,
        )
        with pytest.raises(ValidationError):
            InterviewTurn(
                turn_number=0,  # ge=1
                question=q,
                candidate_answer="...",
                evaluation=ev,
            )

    def test_valid_summary(self):
        summary = InterviewSummary(
            overall_score=82.0,
            category_scores={"Data Structures": 85.0, "OOP": 79.0},
            strengths=["Grounded technical vocabulary"],
            improvement_areas=["Elaborate on edge cases"],
            recommendations=["Practice concurrency questions"],
            questions_answered=3,
            reasoning_provider="rule_based_fallback_v1",
            final_difficulty=DifficultyLevel.ADVANCED,
        )
        assert summary.overall_score == 82.0
        assert summary.questions_answered == 3
        assert summary.reasoning_provider == "rule_based_fallback_v1"

    def test_summary_score_bounds(self):
        with pytest.raises(ValidationError):
            InterviewSummary(
                overall_score=150.0,  # invalid
                questions_answered=1,
                reasoning_provider="rule_based_fallback_v1",
            )
