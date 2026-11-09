"""
Reasoning provider abstraction for VoiceHire AI Adaptive Interview Engine.

Defines the abstract interface (BaseReasoningProvider) for question generation,
candidate answer evaluation, adaptive follow-up selection, and final summary
generation.

This interface is completely decoupled from specific AI backends (e.g. Gnani Evon,
cloud LLMs, or rule-based heuristic engines) so alternative providers can be swapped
without affecting session managers, routers, or client contracts.
"""

from abc import ABC, abstractmethod

from app.models.interview import (
    AnswerEvaluation,
    DifficultyLevel,
    InterviewLanguage,
    InterviewQuestion,
    InterviewSummary,
    InterviewTurn,
)


class BaseReasoningProvider(ABC):
    """
    Abstract contract for adaptive interview reasoning engines.

    Implementations can be rule-based heuristic fallbacks, Gnani Evon API
    connectors, or other LLM-backed services.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the reasoning provider and version."""
        ...

    @abstractmethod
    def generate_initial_question(
        self,
        role: str,
        language: InterviewLanguage = InterviewLanguage.EN_IN,
        difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    ) -> InterviewQuestion:
        """
        Generate or select the initial interview question for a given role,
        language, and starting difficulty.

        Parameters
        ----------
        role : str
            Target job role (e.g. 'Python Developer', 'Data Analyst').
        language : InterviewLanguage
            Language mode (en-IN, te-IN, te-en).
        difficulty : DifficultyLevel
            Initial question difficulty (default: Intermediate).

        Returns
        -------
        InterviewQuestion
            The initial question with expected concepts.
        """
        ...

    @abstractmethod
    def evaluate_answer(
        self,
        question: InterviewQuestion,
        answer_text: str,
        current_difficulty: DifficultyLevel,
    ) -> AnswerEvaluation:
        """
        Evaluate a candidate's transcribed answer against the target question.

        Evaluation must be strictly evidence-based, extracting evidence from
        the candidate's answer without extrapolating unsupported personal
        attributes or claiming permanent lack of ability.

        Parameters
        ----------
        question : InterviewQuestion
            The question that was asked.
        answer_text : str
            The candidate's transcribed answer.
        current_difficulty : DifficultyLevel
            The difficulty level at which the question was posed.

        Returns
        -------
        AnswerEvaluation
            Structured evaluation with score (0-100), strengths, missing concepts,
            evidence quotes, and recommended next difficulty.
        """
        ...

    @abstractmethod
    def generate_follow_up_question(
        self,
        role: str,
        previous_question: InterviewQuestion,
        evaluation: AnswerEvaluation,
        asked_question_ids: set[str],
        language: InterviewLanguage = InterviewLanguage.EN_IN,
    ) -> InterviewQuestion:
        """
        Select or generate an adaptive follow-up question based on the previous
        answer's evaluation and recommended difficulty.

        Avoids repeating questions that were already asked in this session.

        Parameters
        ----------
        role : str
            Target job role.
        previous_question : InterviewQuestion
            The question asked in the previous turn.
        evaluation : AnswerEvaluation
            The evaluation of the candidate's previous answer.
        asked_question_ids : set[str]
            Set of question_ids already asked in this session to prevent repetition.
        language : InterviewLanguage
            Language mode for the follow-up question.

        Returns
        -------
        InterviewQuestion
            The next adaptive question.
        """
        ...

    @abstractmethod
    def generate_final_summary(
        self,
        role: str,
        turns: list[InterviewTurn],
    ) -> InterviewSummary:
        """
        Generate an aggregate performance summary from all recorded interview turns.

        Parameters
        ----------
        role : str
            Target job role.
        turns : list[InterviewTurn]
            All completed question-answer-evaluation turns in the session.

        Returns
        -------
        InterviewSummary
            Aggregate scores, category breakdowns, evidence-grounded strengths,
            improvement areas, and actionable recommendations.
        """
        ...
