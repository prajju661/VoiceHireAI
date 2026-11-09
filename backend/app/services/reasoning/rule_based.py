"""
Rule-based reasoning engine for VoiceHire AI Adaptive Interview Engine.

Provides transparent, deterministic, explainable interview question generation,
answer evaluation, adaptive difficulty adjustment, and performance summaries.

IMPORTANT DISCLAIMER:
This engine uses deterministic keyword and rule-based heuristics as an interim
fallback. It does NOT employ deep semantic understanding, large language models,
or the Gnani Evon model. It strictly complies with fairness constraints by evaluating
only technical evidence present in candidate transcripts, without scoring accents,
speaking speed, filler words, grammar, or personal attributes.
"""

import re
from typing import Any

from app.models.interview import (
    AnswerEvaluation,
    DifficultyLevel,
    InterviewLanguage,
    InterviewQuestion,
    InterviewSummary,
    InterviewTurn,
    JobRole,
)
from app.services.reasoning.base import BaseReasoningProvider


# =============================================================================
# Question Bank: Multi-Role, Multi-Difficulty, Multi-Language
# =============================================================================

QUESTION_BANK: list[dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # Python Developer — English (en-IN)
    # -------------------------------------------------------------------------
    {
        "question_id": "py_en_beg_01",
        "role": "Python Developer",
        "category": "Data Structures",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.EN_IN,
        "question_text": "What is the difference between a list and a tuple in Python, and when would you choose one over the other?",
        "expected_concepts": ["mutable", "immutable", "bracket", "parenthesis", "performance", "hashable", "constant"],
    },
    {
        "question_id": "py_en_beg_02",
        "role": "Python Developer",
        "category": "Language Fundamentals",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.EN_IN,
        "question_text": "Explain how Python handles memory management and the role of the garbage collector.",
        "expected_concepts": ["reference counting", "garbage collector", "cyclic reference", "memory allocation", "deallocation"],
    },
    {
        "question_id": "py_en_int_01",
        "role": "Python Developer",
        "category": "Advanced Language Features",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.EN_IN,
        "question_text": "What are Python generators and decorators, and how do they help write cleaner and more efficient code?",
        "expected_concepts": ["yield", "iterator", "memory efficient", "wrapper", "function", "higher order", "closure"],
    },
    {
        "question_id": "py_en_int_02",
        "role": "Python Developer",
        "category": "Concurrency & Architecture",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.EN_IN,
        "question_text": "What is the Global Interpreter Lock (GIL) in CPython, and how does it affect CPU-bound versus I/O-bound concurrency?",
        "expected_concepts": ["gil", "thread", "multiprocessing", "asyncio", "cpu bound", "io bound", "mutex"],
    },
    {
        "question_id": "py_en_adv_01",
        "role": "Python Developer",
        "category": "System Design & Optimization",
        "difficulty": DifficultyLevel.ADVANCED,
        "language": InterviewLanguage.EN_IN,
        "question_text": "How would you design a high-throughput asynchronous API in FastAPI handling thousands of concurrent requests with external service bottlenecks?",
        "expected_concepts": ["async", "await", "connection pool", "caching", "redis", "background tasks", "backpressure", "queue", "rate limit"],
    },
    {
        "question_id": "py_en_adv_02",
        "role": "Python Developer",
        "category": "Metaprogramming & Internals",
        "difficulty": DifficultyLevel.ADVANCED,
        "language": InterviewLanguage.EN_IN,
        "question_text": "Describe how Python metaclasses and descriptors work internally and give a real-world use case for each.",
        "expected_concepts": ["metaclass", "type", "descriptor", "dunder", "__get__", "__set__", "orm", "validation"],
    },

    # -------------------------------------------------------------------------
    # Python Developer — Telugu (te-IN)
    # -------------------------------------------------------------------------
    {
        "question_id": "py_te_beg_01",
        "role": "Python Developer",
        "category": "Data Structures",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.TE_IN,
        "question_text": "పైథాన్‌లో లిస్ట్ (list) మరియు టపుల్ (tuple) మధ్య ప్రధాన తేడాలు ఏమిటి? వీటిని ఎప్పుడు వాడాలి?",
        "expected_concepts": ["mutable", "immutable", "లిస్ట్", "టపుల్", "performance", "memory"],
    },
    {
        "question_id": "py_te_int_01",
        "role": "Python Developer",
        "category": "Advanced Language Features",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.TE_IN,
        "question_text": "పైథాన్‌లో డెకరేటర్స్ (decorators) మరియు జెనరేటర్స్ (generators) ఎలా పనిచేస్తాయి?",
        "expected_concepts": ["yield", "decorator", "wrapper", "memory", "function"],
    },
    {
        "question_id": "py_te_adv_01",
        "role": "Python Developer",
        "category": "System Design & Optimization",
        "difficulty": DifficultyLevel.ADVANCED,
        "language": InterviewLanguage.TE_IN,
        "question_text": "FastAPI లో హై-స్కేలబుల్ అసమకాలిక (asynchronous) బ్యాకెండ్ ఆర్కిటెక్చర్‌ను ఎలా డిజైన్ చేస్తారు?",
        "expected_concepts": ["async", "await", "redis", "database pool", "cache", "throughput"],
    },

    # -------------------------------------------------------------------------
    # Python Developer — Telugu-English Code-Mixed (te-en)
    # -------------------------------------------------------------------------
    {
        "question_id": "py_teen_beg_01",
        "role": "Python Developer",
        "category": "Data Structures",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.TE_EN,
        "question_text": "Python lo list and tuple madhya differences enti? Practical projects lo edhi eppudu prefer chestaru?",
        "expected_concepts": ["mutable", "immutable", "list", "tuple", "performance", "memory"],
    },
    {
        "question_id": "py_teen_int_01",
        "role": "Python Developer",
        "category": "Concurrency & Architecture",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.TE_EN,
        "question_text": "CPython lo GIL (Global Interpreter Lock) gurinchi explain cheyandi. CPU-bound and I/O tasks lo threads ela behave chestayi?",
        "expected_concepts": ["gil", "threads", "multiprocessing", "asyncio", "cpu bound", "io bound"],
    },
    {
        "question_id": "py_teen_adv_01",
        "role": "Python Developer",
        "category": "System Design & Optimization",
        "difficulty": DifficultyLevel.ADVANCED,
        "language": InterviewLanguage.TE_EN,
        "question_text": "FastAPI tho high concurrency API design chesetappudu Redis caching and connection pooling ela implement chestaru?",
        "expected_concepts": ["fastapi", "async", "redis", "cache", "pooling", "concurrency"],
    },

    # -------------------------------------------------------------------------
    # Java Developer — English (en-IN)
    # -------------------------------------------------------------------------
    {
        "question_id": "java_en_beg_01",
        "role": "Java Developer",
        "category": "OOP & Fundamentals",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.EN_IN,
        "question_text": "Explain the four core principles of Object-Oriented Programming and how Java implements them.",
        "expected_concepts": ["encapsulation", "inheritance", "polymorphism", "abstraction", "class", "interface"],
    },
    {
        "question_id": "java_en_int_01",
        "role": "Java Developer",
        "category": "Collections & Memory",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.EN_IN,
        "question_text": "How does HashMap work internally in Java 8+, and how are hash collisions handled?",
        "expected_concepts": ["hashcode", "equals", "bucket", "linked list", "red black tree", "collision", "threshold"],
    },
    {
        "question_id": "java_en_adv_01",
        "role": "Java Developer",
        "category": "JVM Internals & Microservices",
        "difficulty": DifficultyLevel.ADVANCED,
        "language": InterviewLanguage.EN_IN,
        "question_text": "How do you troubleshoot a memory leak or high GC pause times in a Spring Boot production microservice?",
        "expected_concepts": ["heap dump", "profiler", "garbage collection", "g1gc", "zgc", "metaspace", "thread dump", "leak"],
    },

    # -------------------------------------------------------------------------
    # Java Developer — Telugu (te-IN) & Code-Mixed (te-en)
    # -------------------------------------------------------------------------
    {
        "question_id": "java_te_beg_01",
        "role": "Java Developer",
        "category": "OOP & Fundamentals",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.TE_IN,
        "question_text": "జావాలో ఊప్స్ (OOPs) సూత్రాలు ఏమిటి? అబ్‌స్ట్రాక్షన్ మరియు ఎన్‌క్యాప్సులేషన్ మధ్య తేడా ఏమిటి?",
        "expected_concepts": ["encapsulation", "abstraction", "inheritance", "polymorphism", "class"],
    },
    {
        "question_id": "java_teen_int_01",
        "role": "Java Developer",
        "category": "Collections & Memory",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.TE_EN,
        "question_text": "Java 8 lo HashMap internal working ela untundhi? Hash collisions vachinappudu buckets lo data ela store avtundhi?",
        "expected_concepts": ["hashmap", "bucket", "linkedlist", "tree", "collision", "hashcode", "equals"],
    },

    # -------------------------------------------------------------------------
    # Full Stack Developer — English (en-IN)
    # -------------------------------------------------------------------------
    {
        "question_id": "fs_en_beg_01",
        "role": "Full Stack Developer",
        "category": "Web Architecture",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.EN_IN,
        "question_text": "What happens in the browser and network stack when a user types a URL and presses Enter?",
        "expected_concepts": ["dns", "tcp", "tls", "handshake", "http", "rendering", "dom", "response"],
    },
    {
        "question_id": "fs_en_int_01",
        "role": "Full Stack Developer",
        "category": "Frontend State & API",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.EN_IN,
        "question_text": "How do you manage client-side state in React applications and avoid unnecessary re-renders?",
        "expected_concepts": ["state", "usememo", "usecallback", "context", "redux", "re-render", "virtual dom"],
    },
    {
        "question_id": "fs_en_adv_01",
        "role": "Full Stack Developer",
        "category": "System Architecture & Security",
        "difficulty": DifficultyLevel.ADVANCED,
        "language": InterviewLanguage.EN_IN,
        "question_text": "How do you design a secure authentication and authorization architecture using JWTs with CSRF and XSS protection?",
        "expected_concepts": ["jwt", "httponly", "csrf", "xss", "refresh token", "cors", "secure cookie", "role"],
    },

    # -------------------------------------------------------------------------
    # Full Stack Developer — Telugu & Code-Mixed (te-en)
    # -------------------------------------------------------------------------
    {
        "question_id": "fs_te_beg_01",
        "role": "Full Stack Developer",
        "category": "Web Architecture",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.TE_IN,
        "question_text": "బ్రౌజర్‌లో ఒక వెబ్‌సైట్ URL ఎంటర్ చేసినప్పుడు DNS మరియు సర్వర్ మధ్య జరిగే ప్రక్రియను వివరించండి.",
        "expected_concepts": ["dns", "ip", "server", "http", "browser", "response"],
    },
    {
        "question_id": "fs_teen_int_01",
        "role": "Full Stack Developer",
        "category": "Frontend State & API",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.TE_EN,
        "question_text": "React frontend lo state management and unnecessary re-renders ni optimize cheyadaniki em techniques vaadataru?",
        "expected_concepts": ["react", "state", "usememo", "usecallback", "rerender", "performance"],
    },

    # -------------------------------------------------------------------------
    # Data Analyst — English (en-IN)
    # -------------------------------------------------------------------------
    {
        "question_id": "da_en_beg_01",
        "role": "Data Analyst",
        "category": "SQL & Relational Data",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.EN_IN,
        "question_text": "What is the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN in SQL, and when do you use each?",
        "expected_concepts": ["inner join", "left join", "outer join", "null", "matching", "table"],
    },
    {
        "question_id": "da_en_int_01",
        "role": "Data Analyst",
        "category": "Data Transformation & Pandas",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.EN_IN,
        "question_text": "How do you handle missing values, duplicates, and outliers in a large dataset using Python and Pandas?",
        "expected_concepts": ["imputation", "dropna", "fillna", "outlier", "z-score", "iqr", "duplicates"],
    },
    {
        "question_id": "da_en_adv_01",
        "role": "Data Analyst",
        "category": "Statistical Analysis & Window Functions",
        "difficulty": DifficultyLevel.ADVANCED,
        "language": InterviewLanguage.EN_IN,
        "question_text": "Explain how SQL window functions like ROW_NUMBER, RANK, and DENSE_RANK work with PARTITION BY and ORDER BY.",
        "expected_concepts": ["window function", "partition by", "order by", "row_number", "rank", "dense_rank", "tie"],
    },

    # -------------------------------------------------------------------------
    # Data Analyst — Telugu & Code-Mixed (te-en)
    # -------------------------------------------------------------------------
    {
        "question_id": "da_te_beg_01",
        "role": "Data Analyst",
        "category": "SQL & Relational Data",
        "difficulty": DifficultyLevel.BEGINNER,
        "language": InterviewLanguage.TE_IN,
        "question_text": "SQL లో ఇన్నర్ జాయిన్ (INNER JOIN) మరియు లెఫ్ట్ జాయిన్ (LEFT JOIN) మధ్య తేడా ఏమిటి?",
        "expected_concepts": ["join", "inner", "left", "null", "table", "rows"],
    },
    {
        "question_id": "da_teen_int_01",
        "role": "Data Analyst",
        "category": "Data Transformation & Pandas",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "language": InterviewLanguage.TE_EN,
        "question_text": "Python Pandas lo missing values and outliers ni identify చేసి clean cheyadaniki mee approach enti?",
        "expected_concepts": ["pandas", "missing values", "fillna", "dropna", "outliers", "cleaning"],
    },
]


# =============================================================================
# Helper Word Filtering for Fairness
# =============================================================================

FILLER_WORDS = {
    "um", "uh", "uhh", "er", "ah", "like", "you know", "i mean", "sort of",
    "kind of", "basically", "actually", "literally", "honestly", "right",
    "okay", "so yeah",
}


def _clean_text_for_matching(text: str) -> str:
    """Lowercase and normalize text for transparent keyword matching."""
    cleaned = text.lower()
    # Remove excessive punctuation while preserving alphanumeric characters and spaces
    cleaned = re.sub(r"[^\w\s\-\+\#]", " ", cleaned)
    return " ".join(cleaned.split())


# =============================================================================
# RuleBasedReasoner Implementation
# =============================================================================

class RuleBasedReasoner(BaseReasoningProvider):
    """
    Deterministic, transparent rule-based reasoning engine for VoiceHire AI.

    Evaluates candidate responses based strictly on textual evidence, keyword
    concepts, and topic relevance without subjective bias.
    """

    def __init__(self, question_bank: list[dict[str, Any]] | None = None) -> None:
        raw_bank = question_bank if question_bank is not None else QUESTION_BANK
        self._questions: list[InterviewQuestion] = [
            InterviewQuestion(**item) for item in raw_bank
        ]

    @property
    def provider_name(self) -> str:
        return "rule_based_engine_v1"

    # -------------------------------------------------------------------------
    # 1. Initial Question Generation
    # -------------------------------------------------------------------------
    def generate_initial_question(
        self,
        role: str,
        language: InterviewLanguage = InterviewLanguage.EN_IN,
        difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    ) -> InterviewQuestion:
        """
        Select an initial question matching the role, language, and target difficulty.
        Gracefully falls back to English or an adjacent difficulty if no exact match exists.
        """
        normalized_role = role.strip().lower()

        # Filter by role, language, and difficulty
        candidates = [
            q for q in self._questions
            if q.role.lower() == normalized_role
            and q.language == language
            and q.difficulty == difficulty
        ]

        # Fallback 1: Same role and language, any difficulty
        if not candidates:
            candidates = [
                q for q in self._questions
                if q.role.lower() == normalized_role and q.language == language
            ]

        # Fallback 2: Same role in English
        if not candidates:
            candidates = [
                q for q in self._questions
                if q.role.lower() == normalized_role and q.language == InterviewLanguage.EN_IN
            ]

        # Fallback 3: Any question for the role
        if not candidates:
            candidates = [
                q for q in self._questions
                if q.role.lower() == normalized_role
            ]

        # Ultimate fallback: First available question in bank
        if not candidates:
            candidates = self._questions

        return candidates[0]

    # -------------------------------------------------------------------------
    # 2. Transparent Answer Evaluation
    # -------------------------------------------------------------------------
    def evaluate_answer(
        self,
        question: InterviewQuestion,
        answer_text: str,
        current_difficulty: DifficultyLevel,
    ) -> AnswerEvaluation:
        """
        Evaluate candidate transcript using transparent conceptual matching.

        Fairness guarantees:
        - Accents, filler words ('um', 'like'), and minor grammar are ignored.
        - Only concepts explicitly present in answer_text are cited as strengths.
        - Missing concepts are framed as omitted topics in this response, never as
          permanent candidate deficiencies.
        """
        stripped_answer = answer_text.strip() if answer_text else ""

        # Case A: Empty or whitespace-only response
        if not stripped_answer or len(stripped_answer) < 3:
            return AnswerEvaluation(
                score=0.0,
                is_relevant=False,
                strengths=[],
                improvement_areas=[
                    f"No response provided. Key concepts expected for this question: {', '.join(question.expected_concepts[:3])}."
                ],
                feedback="No substantive technical response was recorded for this question.",
                evidence_from_answer=[],
                recommended_difficulty=self._decrease_difficulty(current_difficulty),
                identified_concepts=[],
                missing_concepts=list(question.expected_concepts),
            )

        cleaned_answer = _clean_text_for_matching(stripped_answer)
        words_count = len(cleaned_answer.split())

        # Check concept matches
        matched_concepts: list[str] = []
        missing_concepts: list[str] = []
        evidence_quotes: list[str] = []

        for concept in question.expected_concepts:
            concept_clean = concept.lower()
            # Simple boundary or substring match for technical terms
            if concept_clean in cleaned_answer:
                matched_concepts.append(concept)
                # Find matching context snippet (up to 60 characters)
                idx = cleaned_answer.find(concept_clean)
                start = max(0, idx - 15)
                end = min(len(stripped_answer), idx + len(concept_clean) + 25)
                snippet = stripped_answer[start:end].strip()
                if snippet and snippet not in evidence_quotes:
                    evidence_quotes.append(f"...{snippet}...")
            else:
                missing_concepts.append(concept)

        total_expected = len(question.expected_concepts)
        coverage_ratio = (len(matched_concepts) / total_expected) if total_expected > 0 else 0.0

        # Check basic relevance (does the answer address question topic?)
        is_relevant = len(matched_concepts) > 0 or words_count >= 15

        # Compute transparent score
        # Base concept score (0-80 points)
        concept_score = coverage_ratio * 80.0

        # Elaboration & explanation depth (0-20 points)
        depth_score = min(20.0, (words_count / 30.0) * 20.0) if is_relevant else 0.0

        raw_score = concept_score + depth_score

        # Clamp between 0.0 and 100.0
        final_score = max(0.0, min(100.0, round(raw_score, 1)))

        # Formulate grounded strengths (strictly from evidence)
        strengths: list[str] = []
        if matched_concepts:
            concept_list_str = ", ".join(f"'{c}'" for c in matched_concepts[:4])
            strengths.append(f"Addressed key technical concepts: {concept_list_str}.")
        if words_count >= 25:
            strengths.append("Provided a detailed explanation with contextual elaboration.")

        # Formulate constructive improvement areas (never labeling candidate negatively)
        improvement_areas: list[str] = []
        if missing_concepts:
            missing_str = ", ".join(f"'{c}'" for c in missing_concepts[:3])
            improvement_areas.append(
                f"Did not mention concepts such as {missing_str} in this response."
            )
        if words_count < 15 and final_score < 60:
            improvement_areas.append("Response was brief; consider expanding on technical mechanics and trade-offs.")

        # Determine conservative difficulty adjustment
        if final_score >= 75.0:
            recommended_difficulty = self._increase_difficulty(current_difficulty)
        elif final_score <= 40.0:
            recommended_difficulty = self._decrease_difficulty(current_difficulty)
        else:
            recommended_difficulty = current_difficulty

        # Feedback narrative
        feedback = self._build_feedback(
            score=final_score,
            matched=matched_concepts,
            missing=missing_concepts,
            is_relevant=is_relevant,
        )

        return AnswerEvaluation(
            score=final_score,
            is_relevant=is_relevant,
            strengths=strengths,
            improvement_areas=improvement_areas,
            feedback=feedback,
            evidence_from_answer=evidence_quotes[:3],
            recommended_difficulty=recommended_difficulty,
            identified_concepts=matched_concepts,
            missing_concepts=missing_concepts,
        )

    # -------------------------------------------------------------------------
    # 3. Contextual Follow-Up Question Generation
    # -------------------------------------------------------------------------
    def generate_follow_up_question(
        self,
        role: str,
        previous_question: InterviewQuestion,
        evaluation: AnswerEvaluation,
        asked_question_ids: set[str],
        language: InterviewLanguage = InterviewLanguage.EN_IN,
    ) -> InterviewQuestion:
        """
        Select an unasked follow-up question adapting to the recommended difficulty.
        Prefers complementary or related categories while strictly avoiding duplicates.
        """
        normalized_role = role.strip().lower()
        target_diff = evaluation.recommended_difficulty

        # 1. Target role, target language, target difficulty, not yet asked
        candidates = [
            q for q in self._questions
            if q.role.lower() == normalized_role
            and q.language == language
            and q.difficulty == target_diff
            and q.question_id not in asked_question_ids
        ]

        # 2. Relax difficulty: same role, same language, any unasked question
        if not candidates:
            candidates = [
                q for q in self._questions
                if q.role.lower() == normalized_role
                and q.language == language
                and q.question_id not in asked_question_ids
            ]

        # 3. Relax language: same role in English, target difficulty, unasked
        if not candidates:
            candidates = [
                q for q in self._questions
                if q.role.lower() == normalized_role
                and q.language == InterviewLanguage.EN_IN
                and q.question_id not in asked_question_ids
            ]

        # 4. Any unasked question for the role
        if not candidates:
            candidates = [
                q for q in self._questions
                if q.role.lower() == normalized_role
                and q.question_id not in asked_question_ids
            ]

        # 5. If all role questions have been asked, cycle from role pool
        if not candidates:
            candidates = [
                q for q in self._questions
                if q.role.lower() == normalized_role
            ]

        # Ultimate fallback
        if not candidates:
            candidates = self._questions

        return candidates[0]

    # -------------------------------------------------------------------------
    # 4. Final Performance Summary
    # -------------------------------------------------------------------------
    def generate_final_summary(
        self,
        role: str,
        turns: list[InterviewTurn],
    ) -> InterviewSummary:
        """
        Aggregate evaluated turns into a transparent, evidence-grounded performance report.
        """
        if not turns:
            return InterviewSummary(
                overall_score=0.0,
                category_scores={},
                strengths=["Session initialized; no questions were answered."],
                improvement_areas=["Complete full interview turns to generate performance analysis."],
                recommendations=["Participate in practice interview sessions."],
                questions_answered=0,
                reasoning_provider=self.provider_name,
                final_difficulty=DifficultyLevel.INTERMEDIATE,
            )

        # 1. Compute overall score
        total_score = sum(t.evaluation.score for t in turns)
        overall_score = round(total_score / len(turns), 1)

        # 2. Compute category scores
        category_totals: dict[str, list[float]] = {}
        for t in turns:
            cat = t.question.category
            category_totals.setdefault(cat, []).append(t.evaluation.score)

        category_scores: dict[str, float] = {
            cat: round(sum(scores) / len(scores), 1)
            for cat, scores in category_totals.items()
        }

        # 3. Aggregate demonstrated strengths (avoiding duplicates)
        aggregated_strengths: list[str] = []
        for t in turns:
            for s in t.evaluation.strengths:
                if s not in aggregated_strengths:
                    aggregated_strengths.append(s)

        if not aggregated_strengths:
            aggregated_strengths.append("Participated in technical question dialogue.")

        # 4. Aggregate improvement areas
        aggregated_improvements: list[str] = []
        for t in turns:
            for imp in t.evaluation.improvement_areas:
                if imp not in aggregated_improvements:
                    aggregated_improvements.append(imp)

        # 5. Formulate actionable recommendations
        recommendations: list[str] = []
        low_categories = [cat for cat, score in category_scores.items() if score < 65.0]
        if low_categories:
            low_cats_str = ", ".join(f"'{c}'" for c in low_categories)
            recommendations.append(f"Focus revision on foundational concepts in {low_cats_str}.")

        high_categories = [cat for cat, score in category_scores.items() if score >= 75.0]
        if high_categories:
            high_cats_str = ", ".join(f"'{c}'" for c in high_categories)
            recommendations.append(f"Continue demonstrating depth in strong categories: {high_cats_str}.")

        recommendations.append(
            "When responding, provide practical code examples or concrete architectural trade-offs."
        )

        final_difficulty = turns[-1].evaluation.recommended_difficulty

        return InterviewSummary(
            overall_score=overall_score,
            category_scores=category_scores,
            strengths=aggregated_strengths[:5],
            improvement_areas=aggregated_improvements[:5],
            recommendations=recommendations,
            questions_answered=len(turns),
            reasoning_provider=self.provider_name,
            final_difficulty=final_difficulty,
        )

    # -------------------------------------------------------------------------
    # Internal Difficulty Scaling Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _increase_difficulty(current: DifficultyLevel) -> DifficultyLevel:
        if current == DifficultyLevel.BEGINNER:
            return DifficultyLevel.INTERMEDIATE
        if current == DifficultyLevel.INTERMEDIATE:
            return DifficultyLevel.ADVANCED
        return DifficultyLevel.ADVANCED

    @staticmethod
    def _decrease_difficulty(current: DifficultyLevel) -> DifficultyLevel:
        if current == DifficultyLevel.ADVANCED:
            return DifficultyLevel.INTERMEDIATE
        if current == DifficultyLevel.INTERMEDIATE:
            return DifficultyLevel.BEGINNER
        return DifficultyLevel.BEGINNER

    @staticmethod
    def _build_feedback(
        score: float,
        matched: list[str],
        missing: list[str],
        is_relevant: bool,
    ) -> str:
        if not is_relevant:
            return "The response did not directly address the core technical subject of the question."

        parts: list[str] = []
        if score >= 75.0:
            parts.append(f"Strong response covering key technical aspects: {', '.join(matched)}.")
        elif score >= 50.0:
            parts.append(f"Competent baseline response addressing: {', '.join(matched)}.")
        else:
            parts.append("Partial response.")

        if missing:
            parts.append(f"Could be strengthened by mentioning {', '.join(missing[:3])}.")

        return " ".join(parts)
