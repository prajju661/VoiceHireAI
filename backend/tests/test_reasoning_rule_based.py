"""
Unit tests for VoiceHire AI Rule-Based Reasoning Engine (Phase 5A1).

Verifies:
1. BaseReasoningProvider interface compatibility.
2. Initial question generation for all 4 supported roles and 3 languages.
3. Transparent conceptual answer evaluation and scoring.
4. Adaptive difficulty scaling:
   - Strong answer increases difficulty.
   - Weak/incomplete answer decreases difficulty.
   - Moderate answer maintains difficulty.
5. Contextual follow-up question selection without repeating asked questions.
6. Final summary report generation with category breakdowns.
7. Fairness rules:
   - Ignores filler words ('um', 'uh', 'like', 'you know').
   - Grounded evidence only — does not hallucinate candidate skills.
   - Constructive missing concept identification.
"""

from app.models.interview import (
    DifficultyLevel,
    InterviewLanguage,
    InterviewQuestion,
    InterviewTurn,
    JobRole,
)
from app.services.reasoning.base import BaseReasoningProvider
from app.services.reasoning.rule_based import RuleBasedReasoner


class TestReasoningInterfaceAndInitialization:
    """Verify provider polymorphism and contract compliance."""

    def test_implements_base_provider_interface(self):
        engine = RuleBasedReasoner()
        assert isinstance(engine, BaseReasoningProvider)
        assert engine.provider_name == "rule_based_engine_v1"


class TestRoleAndLanguageQuestionGeneration:
    """Verify initial question generation across all supported roles and languages."""

    def setup_method(self):
        self.engine = RuleBasedReasoner()

    def test_each_supported_role_generates_initial_question(self):
        roles = [
            "Python Developer",
            "Java Developer",
            "Full Stack Developer",
            "Data Analyst",
        ]
        for role in roles:
            q = self.engine.generate_initial_question(role, language=InterviewLanguage.EN_IN)
            assert isinstance(q, InterviewQuestion)
            assert q.role.lower() == role.lower()
            assert len(q.question_text) > 10
            assert len(q.expected_concepts) > 0

    def test_each_supported_language_generates_question(self):
        languages = [
            InterviewLanguage.EN_IN,
            InterviewLanguage.TE_IN,
            InterviewLanguage.TE_EN,
        ]
        for lang in languages:
            q = self.engine.generate_initial_question(
                role="Python Developer",
                language=lang,
                difficulty=DifficultyLevel.BEGINNER,
            )
            assert isinstance(q, InterviewQuestion)
            assert q.language == lang


class TestAnswerEvaluationAndEvidence:
    """Verify transparent scoring, evidence extraction, and missing concept detection."""

    def setup_method(self):
        self.engine = RuleBasedReasoner()
        self.question = InterviewQuestion(
            question_id="test_py_01",
            role="Python Developer",
            category="Data Structures",
            difficulty=DifficultyLevel.BEGINNER,
            language=InterviewLanguage.EN_IN,
            question_text="What is the difference between a list and a tuple in Python?",
            expected_concepts=["mutable", "immutable", "performance", "hashable"],
        )

    def test_strong_answer_high_score_and_difficulty_increase(self):
        answer = (
            "A list in Python is mutable, meaning elements can be modified. "
            "In contrast, a tuple is immutable and cannot be changed after creation. "
            "Tuples have better performance and are hashable so they can be dict keys."
        )
        evaluation = self.engine.evaluate_answer(
            self.question, answer, current_difficulty=DifficultyLevel.BEGINNER
        )

        assert evaluation.score >= 75.0
        assert evaluation.is_relevant is True
        assert "mutable" in evaluation.identified_concepts
        assert "immutable" in evaluation.identified_concepts
        assert len(evaluation.evidence_from_answer) > 0
        # Beginner -> Intermediate
        assert evaluation.recommended_difficulty == DifficultyLevel.INTERMEDIATE

    def test_moderate_answer_maintains_difficulty(self):
        answer = "A list is mutable while a tuple is immutable in Python."
        evaluation = self.engine.evaluate_answer(
            self.question, answer, current_difficulty=DifficultyLevel.INTERMEDIATE
        )

        assert 45.0 <= evaluation.score <= 74.0
        assert evaluation.recommended_difficulty == DifficultyLevel.INTERMEDIATE
        assert "performance" in evaluation.missing_concepts

    def test_weak_answer_low_score_and_difficulty_decrease(self):
        answer = "Lists have square brackets."
        evaluation = self.engine.evaluate_answer(
            self.question, answer, current_difficulty=DifficultyLevel.ADVANCED
        )

        assert evaluation.score <= 40.0
        # Advanced -> Intermediate
        assert evaluation.recommended_difficulty == DifficultyLevel.INTERMEDIATE
        assert len(evaluation.missing_concepts) > 0

    def test_empty_answer_scores_zero(self):
        evaluation = self.engine.evaluate_answer(
            self.question, "", current_difficulty=DifficultyLevel.INTERMEDIATE
        )
        assert evaluation.score == 0.0
        assert evaluation.is_relevant is False
        assert evaluation.recommended_difficulty == DifficultyLevel.BEGINNER
        assert len(evaluation.missing_concepts) == len(self.question.expected_concepts)

    def test_whitespace_answer_scores_zero(self):
        evaluation = self.engine.evaluate_answer(
            self.question, "   \n\t  ", current_difficulty=DifficultyLevel.INTERMEDIATE
        )
        assert evaluation.score == 0.0
        assert evaluation.is_relevant is False


class TestAdaptiveDifficultyProgression:
    """Verify conservative difficulty transitions across all tiers."""

    def setup_method(self):
        self.engine = RuleBasedReasoner()
        self.question = InterviewQuestion(
            question_id="test_generic",
            role="Python Developer",
            category="Data Structures",
            difficulty=DifficultyLevel.BEGINNER,
            question_text="Sample question",
            expected_concepts=["concept1", "concept2"],
        )

    def test_strong_answer_beginner_to_intermediate(self):
        ans = "This answer explains concept1 and concept2 thoroughly with deep context."
        ev = self.engine.evaluate_answer(self.question, ans, DifficultyLevel.BEGINNER)
        assert ev.recommended_difficulty == DifficultyLevel.INTERMEDIATE

    def test_strong_answer_intermediate_to_advanced(self):
        ans = "This answer explains concept1 and concept2 thoroughly with deep context."
        ev = self.engine.evaluate_answer(self.question, ans, DifficultyLevel.INTERMEDIATE)
        assert ev.recommended_difficulty == DifficultyLevel.ADVANCED

    def test_strong_answer_advanced_capped_at_advanced(self):
        ans = "This answer explains concept1 and concept2 thoroughly with deep context."
        ev = self.engine.evaluate_answer(self.question, ans, DifficultyLevel.ADVANCED)
        assert ev.recommended_difficulty == DifficultyLevel.ADVANCED

    def test_weak_answer_advanced_to_intermediate(self):
        ev = self.engine.evaluate_answer(self.question, "Unrelated reply.", DifficultyLevel.ADVANCED)
        assert ev.recommended_difficulty == DifficultyLevel.INTERMEDIATE

    def test_weak_answer_intermediate_to_beginner(self):
        ev = self.engine.evaluate_answer(self.question, "Unrelated reply.", DifficultyLevel.INTERMEDIATE)
        assert ev.recommended_difficulty == DifficultyLevel.BEGINNER

    def test_weak_answer_beginner_floored_at_beginner(self):
        ev = self.engine.evaluate_answer(self.question, "Unrelated reply.", DifficultyLevel.BEGINNER)
        assert ev.recommended_difficulty == DifficultyLevel.BEGINNER


class TestFollowUpQuestionGeneration:
    """Verify follow-up selection adapts to difficulty and avoids repetition."""

    def setup_method(self):
        self.engine = RuleBasedReasoner()

    def test_follow_up_avoids_asked_questions(self):
        initial = self.engine.generate_initial_question(
            "Python Developer", language=InterviewLanguage.EN_IN, difficulty=DifficultyLevel.BEGINNER
        )

        ev = self.engine.evaluate_answer(
            initial,
            "A list is mutable and a tuple is immutable with better performance.",
            current_difficulty=DifficultyLevel.BEGINNER,
        )

        asked = {initial.question_id}
        follow_up = self.engine.generate_follow_up_question(
            role="Python Developer",
            previous_question=initial,
            evaluation=ev,
            asked_question_ids=asked,
            language=InterviewLanguage.EN_IN,
        )

        assert follow_up.question_id not in asked
        assert follow_up.role == "Python Developer"

    def test_follow_up_adapts_to_recommended_difficulty(self):
        q = self.engine.generate_initial_question("Java Developer", difficulty=DifficultyLevel.BEGINNER)
        strong_ans = (
            "Encapsulation, inheritance, polymorphism, and abstraction are the four OOP principles in Java. "
            "Classes and interfaces implement these."
        )
        ev = self.engine.evaluate_answer(q, strong_ans, DifficultyLevel.BEGINNER)
        assert ev.recommended_difficulty == DifficultyLevel.INTERMEDIATE

        follow_up = self.engine.generate_follow_up_question(
            role="Java Developer",
            previous_question=q,
            evaluation=ev,
            asked_question_ids={q.question_id},
        )
        # Should target intermediate level
        assert follow_up.difficulty == DifficultyLevel.INTERMEDIATE


class TestFinalSummaryGeneration:
    """Verify aggregated score, category metrics, and constructive feedback."""

    def setup_method(self):
        self.engine = RuleBasedReasoner()

    def test_summary_aggregates_multiple_turns(self):
        q1 = self.engine.generate_initial_question("Python Developer", difficulty=DifficultyLevel.BEGINNER)
        ev1 = self.engine.evaluate_answer(
            q1, "A list is mutable and a tuple is immutable.", DifficultyLevel.BEGINNER
        )

        q2 = self.engine.generate_follow_up_question(
            "Python Developer", q1, ev1, asked_question_ids={q1.question_id}
        )
        ev2 = self.engine.evaluate_answer(
            q2, "Generators use yield for memory efficient iteration.", ev1.recommended_difficulty
        )

        turns = [
            InterviewTurn(turn_number=1, question=q1, candidate_answer="A list is mutable...", evaluation=ev1),
            InterviewTurn(turn_number=2, question=q2, candidate_answer="Generators use yield...", evaluation=ev2),
        ]

        summary = self.engine.generate_final_summary("Python Developer", turns)

        assert summary.questions_answered == 2
        assert 0.0 <= summary.overall_score <= 100.0
        assert len(summary.category_scores) >= 1
        assert len(summary.strengths) > 0
        assert len(summary.recommendations) > 0
        assert summary.reasoning_provider == "rule_based_engine_v1"

    def test_summary_empty_turns_safe(self):
        summary = self.engine.generate_final_summary("Python Developer", [])
        assert summary.questions_answered == 0
        assert summary.overall_score == 0.0


class TestFairnessAndEvidenceRules:
    """Verify fairness guarantees: no bias on filler words, no skill hallucinations."""

    def setup_method(self):
        self.engine = RuleBasedReasoner()
        self.question = InterviewQuestion(
            question_id="fairness_q1",
            role="Python Developer",
            category="Data Structures",
            difficulty=DifficultyLevel.BEGINNER,
            question_text="Explain list vs tuple in Python.",
            expected_concepts=["mutable", "immutable"],
        )

    def test_filler_words_do_not_lower_score(self):
        clean_answer = "Lists are mutable and tuples are immutable."
        filler_answer = "Um, like, you know, lists are, basically, mutable and tuples are, uh, immutable, you know."

        ev_clean = self.engine.evaluate_answer(self.question, clean_answer, DifficultyLevel.BEGINNER)
        ev_filler = self.engine.evaluate_answer(self.question, filler_answer, DifficultyLevel.BEGINNER)

        # Both answers provide the exact same technical concepts ('mutable', 'immutable')
        assert ev_filler.score >= ev_clean.score - 5.0
        assert "mutable" in ev_filler.identified_concepts
        assert "immutable" in ev_filler.identified_concepts

    def test_evidence_grounding_no_hallucinated_skills(self):
        answer = "In Python, lists are mutable."
        ev = self.engine.evaluate_answer(self.question, answer, DifficultyLevel.BEGINNER)

        # Only concepts actually in the answer should be in identified_concepts
        assert "mutable" in ev.identified_concepts
        assert "immutable" not in ev.identified_concepts
        # Evidence quotes must be from the actual text
        for quote in ev.evidence_from_answer:
            assert "mutable" in quote

    def test_missing_concepts_framed_constructively(self):
        answer = "Lists are mutable."
        ev = self.engine.evaluate_answer(self.question, answer, DifficultyLevel.BEGINNER)

        # Missing concept is immutable
        assert "immutable" in ev.missing_concepts
        # Check that feedback does NOT say 'candidate lacks ability' or similar defamatory claims
        for imp in ev.improvement_areas:
            assert "incompetent" not in imp.lower()
            assert "lacks ability" not in imp.lower()
            assert "never" not in imp.lower()
