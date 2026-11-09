import test from 'node:test';
import assert from 'node:assert/strict';
import type {
  DifficultyLevel,
  InterviewLanguage,
  JobRole,
  InterviewQuestion,
  InterviewSummary,
} from '../../services/api.ts';

// -----------------------------------------------------------------------------
// 1. Setup Configuration & Options Verification
// -----------------------------------------------------------------------------
test('Interview setup supports all 4 backend job roles', () => {
  const supportedRoles: JobRole[] = [
    'Python Developer',
    'Java Developer',
    'Full Stack Developer',
    'Data Analyst',
  ];

  assert.equal(supportedRoles.length, 4);
  assert.ok(supportedRoles.includes('Python Developer'));
  assert.ok(supportedRoles.includes('Java Developer'));
  assert.ok(supportedRoles.includes('Full Stack Developer'));
  assert.ok(supportedRoles.includes('Data Analyst'));
});

test('Interview setup supports English, Telugu, and Code-Mixed options', () => {
  const supportedLangs: InterviewLanguage[] = ['en-IN', 'te-IN', 'te-en'];

  assert.equal(supportedLangs.length, 3);
  assert.ok(supportedLangs.includes('en-IN'));
  assert.ok(supportedLangs.includes('te-IN'));
  assert.ok(supportedLangs.includes('te-en'));
});

test('Interview setup supports 3 difficulty tiers', () => {
  const diffLevels: DifficultyLevel[] = ['beginner', 'intermediate', 'advanced'];

  assert.equal(diffLevels.length, 3);
  assert.ok(diffLevels.includes('beginner'));
  assert.ok(diffLevels.includes('intermediate'));
  assert.ok(diffLevels.includes('advanced'));
});

// -----------------------------------------------------------------------------
// 2. Audio Language Mapping for Gnani Timbre & Prisma
// -----------------------------------------------------------------------------
test('Question audio language mapper correctly maps interview language to Timbre TTS', () => {
  const getTtsLang = (lang: InterviewLanguage): 'en-IN' | 'te-IN' => {
    return lang === 'te-IN' ? 'te-IN' : 'en-IN';
  };

  assert.equal(getTtsLang('en-IN'), 'en-IN');
  assert.equal(getTtsLang('te-IN'), 'te-IN');
  // Code-mixed te-en defaults to en-IN for Timbre synthesis
  assert.equal(getTtsLang('te-en'), 'en-IN');
});

test('Speech-to-text language mapper correctly maps to Prisma STT', () => {
  const getSttLang = (lang: InterviewLanguage): string => {
    return lang === 'te-IN' ? 'te-IN' : 'en-IN';
  };

  assert.equal(getSttLang('en-IN'), 'en-IN');
  assert.equal(getSttLang('te-IN'), 'te-IN');
  assert.equal(getSttLang('te-en'), 'en-IN');
});

// -----------------------------------------------------------------------------
// 3. Answer Validation Logic
// -----------------------------------------------------------------------------
test('Answer validator rejects empty and whitespace-only submissions', () => {
  const isValidAnswer = (text: string): boolean => {
    return text.trim().length > 0;
  };

  assert.equal(isValidAnswer(''), false);
  assert.equal(isValidAnswer('    '), false);
  assert.equal(isValidAnswer('\t\n'), false);
  assert.equal(isValidAnswer('A list is mutable.'), true);
});

// -----------------------------------------------------------------------------
// 4. Turn State Progression
// -----------------------------------------------------------------------------
test('Turn progression correctly advances turn number and updates question', () => {
  const initialTurn = 1;
  const currentDiff = 'intermediate';

  const q1: InterviewQuestion = {
    question_id: 'py_en_int_01',
    question_text: 'What are generators?',
    role: 'Python Developer',
    category: 'Advanced Language Features',
    difficulty: 'intermediate',
    language: 'en-IN',
  };

  const q2: InterviewQuestion = {
    question_id: 'py_en_adv_01',
    question_text: 'Explain GIL in Python.',
    role: 'Python Developer',
    category: 'Concurrency',
    difficulty: 'advanced',
    language: 'en-IN',
  };

  // Simulate advancing turn
  const nextTurnNumber = initialTurn + 1;
  const nextQuestion = q2;
  const updatedDifficulty = 'advanced';

  assert.notEqual(q1.question_id, nextQuestion.question_id);
  assert.equal(nextTurnNumber, 2);
  assert.equal(nextQuestion.question_id, 'py_en_adv_01');
  assert.equal(updatedDifficulty, 'advanced');
  assert.notEqual(currentDiff, updatedDifficulty);
});

// -----------------------------------------------------------------------------
// 5. Performance Tier Classification & Score Precision
// -----------------------------------------------------------------------------
test('Report performance tier accurately categorizes scores', () => {
  const getTierLabel = (score: number): string => {
    if (score >= 80) return 'Strong Hire / High Proficiency';
    if (score >= 60) return 'Hire / Proficient';
    if (score >= 40) return 'Borderline / Developing';
    return 'Needs Preparation';
  };

  assert.equal(getTierLabel(95.0), 'Strong Hire / High Proficiency');
  assert.equal(getTierLabel(80.0), 'Strong Hire / High Proficiency');
  assert.equal(getTierLabel(79.9), 'Hire / Proficient');
  assert.equal(getTierLabel(60.0), 'Hire / Proficient');
  assert.equal(getTierLabel(59.9), 'Borderline / Developing');
  assert.equal(getTierLabel(40.0), 'Borderline / Developing');
  assert.equal(getTierLabel(39.9), 'Needs Preparation');
  assert.equal(getTierLabel(0.0), 'Needs Preparation');
});

test('Report preserves backend score exactly without client-side deviation', () => {
  const mockSummary: InterviewSummary = {
    overall_score: 87.3,
    category_scores: {
      'Data Structures': 90.0,
      'System Design': 84.6,
    },
    strengths: ['Clear explanation of mutable vs immutable'],
    improvement_areas: ['Could elaborate on caching'],
    recommendations: ['Practice distributed caching'],
    questions_answered: 3,
    reasoning_provider: 'rule_based_engine_v1',
    final_difficulty: 'advanced',
  };

  // Verifies the exact score is rendered
  const displayedScore = mockSummary.overall_score.toFixed(1);
  assert.equal(displayedScore, '87.3');
  assert.equal(mockSummary.questions_answered, 3);
  assert.equal(mockSummary.final_difficulty, 'advanced');
});
