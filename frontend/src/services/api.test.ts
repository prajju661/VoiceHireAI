import test from 'node:test';
import assert from 'node:assert/strict';
import {
  startInterview,
  submitAnswer,
  getInterviewSession,
  completeInterview,
  listInterviews,
  deleteInterview,
  API_BASE_URL,
} from './api.ts';

// Save original global fetch
const originalFetch = globalThis.fetch;

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('startInterview sends expected request payload and returns session', async () => {
  let capturedUrl = '';
  let capturedMethod = '';
  let capturedHeaders: Record<string, string> = {};
  let capturedBody = '';

  globalThis.fetch = async (input, init) => {
    capturedUrl = input.toString();
    capturedMethod = init?.method || 'GET';
    capturedHeaders = (init?.headers || {}) as Record<string, string>;
    capturedBody = (init?.body as string) || '';

    const mockResponse = {
      session_id: 'session-uuid-1234',
      candidate_name: 'Priya Sharma',
      candidate_email: 'priya@example.com',
      job_role: 'Python Developer',
      language: 'en-IN',
      current_difficulty: 'intermediate',
      status: 'active',
      reasoning_provider: 'rule_based_engine_v1',
      first_question: {
        question_id: 'py_en_int_01',
        question_text: 'What are Python generators and decorators?',
        role: 'Python Developer',
        category: 'Advanced Language Features',
        difficulty: 'intermediate',
        language: 'en-IN',
        expected_concepts: ['yield', 'decorator'],
      },
      turn_number: 1,
      created_at: '2026-11-09T14:00:00Z',
    };

    return new Response(JSON.stringify(mockResponse), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const result = await startInterview({
    job_role: 'Python Developer',
    language: 'en-IN',
    initial_difficulty: 'intermediate',
    candidate_name: 'Priya Sharma',
    candidate_email: 'priya@example.com',
  });

  assert.equal(capturedUrl, `${API_BASE_URL}/api/interview/start`);
  assert.equal(capturedMethod, 'POST');
  assert.equal(capturedHeaders['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(capturedBody), {
    job_role: 'Python Developer',
    language: 'en-IN',
    initial_difficulty: 'intermediate',
    candidate_name: 'Priya Sharma',
    candidate_email: 'priya@example.com',
  });
  assert.equal(result.session_id, 'session-uuid-1234');
  assert.equal(result.turn_number, 1);
  assert.equal(result.first_question.question_id, 'py_en_int_01');
});

test('startInterview surfaces backend error detail on failure', async () => {
  globalThis.fetch = async () => {
    return new Response(
      JSON.stringify({ detail: 'Invalid job role specified.' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } }
    );
  };

  await assert.rejects(
    async () => {
      await startInterview({ job_role: 'Unsupported' });
    },
    (err: Error) => {
      assert.match(err.message, /Invalid job role specified/);
      return true;
    }
  );
});

test('submitAnswer sends answer text and returns evaluation and next question', async () => {
  let capturedUrl = '';
  let capturedBody = '';

  globalThis.fetch = async (input, init) => {
    capturedUrl = input.toString();
    capturedBody = (init?.body as string) || '';

    const mockResponse = {
      session_id: 'session-uuid-1234',
      turn_number: 1,
      score: 85.5,
      feedback: 'Good explanation of generators and decorators.',
      strengths: ['Identified yield keyword', 'Explained wrapper functions'],
      improvement_areas: ['Could mention closure mechanics'],
      evidence_from_answer: ['generators use yield to return lazy iterators'],
      next_question: {
        question_id: 'py_en_adv_01',
        question_text: 'How would you design a high-throughput async API in FastAPI?',
        role: 'Python Developer',
        category: 'System Design & Optimization',
        difficulty: 'advanced',
        language: 'en-IN',
        expected_concepts: ['async', 'redis'],
      },
      updated_difficulty: 'advanced',
      session_status: 'active',
    };

    return new Response(JSON.stringify(mockResponse), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const result = await submitAnswer('session-uuid-1234', {
    answer_text: 'Generators use yield to return lazy iterators for memory efficiency.',
  });

  assert.equal(
    capturedUrl,
    `${API_BASE_URL}/api/interview/session-uuid-1234/answer`
  );
  assert.deepEqual(JSON.parse(capturedBody), {
    answer_text: 'Generators use yield to return lazy iterators for memory efficiency.',
  });
  assert.equal(result.score, 85.5);
  assert.equal(result.updated_difficulty, 'advanced');
  assert.equal(result.next_question.question_id, 'py_en_adv_01');
});

test('submitAnswer raises 404 when session is not found', async () => {
  globalThis.fetch = async () => {
    return new Response(
      JSON.stringify({ detail: "Interview session 'missing-id' not found." }),
      { status: 404, headers: { 'Content-Type': 'application/json' } }
    );
  };

  await assert.rejects(
    async () => {
      await submitAnswer('missing-id', { answer_text: 'Some response' });
    },
    (err: Error) => {
      assert.match(err.message, /not found/);
      return true;
    }
  );
});

test('getInterviewSession retrieves complete turns and running score', async () => {
  let capturedUrl = '';

  globalThis.fetch = async (input) => {
    capturedUrl = input.toString();
    const mockDetails = {
      session_id: 'session-123',
      candidate_name: 'Bob',
      candidate_email: 'bob@example.com',
      job_role: 'Data Analyst',
      language: 'en-IN',
      current_difficulty: 'beginner',
      status: 'active',
      reasoning_provider: 'rule_based_engine_v1',
      overall_score: 75.0,
      created_at: '2026-11-09T14:10:00Z',
      updated_at: '2026-11-09T14:15:00Z',
      completed_at: null,
      turns_count: 1,
      turns: [
        {
          id: 'turn-1',
          session_id: 'session-123',
          turn_number: 1,
          question_id: 'da_en_beg_01',
          question_text: 'Difference between INNER JOIN and LEFT JOIN?',
          question_category: 'SQL & Relational Data',
          question_difficulty: 'beginner',
          question_language: 'en-IN',
          answer_text: 'Inner join gives matching rows.',
          score: 75.0,
          feedback: 'Accurate distinction.',
          strengths: ['Identified matching rows'],
          improvement_areas: ['Explain null handling in right table'],
          evidence_from_answer: ['matching rows'],
          created_at: '2026-11-09T14:10:00Z',
          answered_at: '2026-11-09T14:12:00Z',
        },
      ],
    };

    return new Response(JSON.stringify(mockDetails), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const details = await getInterviewSession('session-123');
  assert.equal(capturedUrl, `${API_BASE_URL}/api/interview/session-123`);
  assert.equal(details.session_id, 'session-123');
  assert.equal(details.overall_score, 75.0);
  assert.equal(details.turns.length, 1);
  assert.equal(details.turns[0].turn_number, 1);
});

test('completeInterview concludes session and generates summary scorecard', async () => {
  let capturedUrl = '';
  let capturedMethod = '';

  globalThis.fetch = async (input, init) => {
    capturedUrl = input.toString();
    capturedMethod = init?.method || 'GET';

    const mockSummary = {
      overall_score: 82.5,
      category_scores: {
        'Data Structures': 85.0,
        'Concurrency & Architecture': 80.0,
      },
      strengths: ['Strong fundamentals in immutable collections'],
      improvement_areas: ['Deepen understanding of thread synchronization'],
      recommendations: ['Study asyncio event loop internals'],
      questions_answered: 2,
      reasoning_provider: 'rule_based_engine_v1',
      final_difficulty: 'intermediate',
    };

    return new Response(JSON.stringify(mockSummary), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const summary = await completeInterview('session-123');
  assert.equal(
    capturedUrl,
    `${API_BASE_URL}/api/interview/session-123/complete`
  );
  assert.equal(capturedMethod, 'POST');
  assert.equal(summary.overall_score, 82.5);
  assert.equal(summary.questions_answered, 2);
  assert.equal(summary.final_difficulty, 'intermediate');
  assert.equal(summary.strengths.length, 1);
});

test('listInterviews passes limit and offset query parameters', async () => {
  let capturedUrl = '';

  globalThis.fetch = async (input) => {
    capturedUrl = input.toString();
    const mockList = {
      total: 1,
      limit: 10,
      offset: 0,
      sessions: [
        {
          id: 's-1',
          job_role: 'Python Developer',
          language: 'en-IN',
          difficulty: 'intermediate',
          status: 'completed',
          reasoning_provider: 'rule_based_engine_v1',
          overall_score: 88.0,
          candidate_name: 'Priya',
          candidate_email: null,
          created_at: '2026-11-09T14:00:00Z',
          updated_at: '2026-11-09T14:20:00Z',
          completed_at: '2026-11-09T14:20:00Z',
        },
      ],
    };

    return new Response(JSON.stringify(mockList), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const data = await listInterviews(10, 0);
  assert.equal(capturedUrl, `${API_BASE_URL}/api/interview?limit=10&offset=0`);
  assert.equal(data.total, 1);
  assert.equal(data.sessions[0].overall_score, 88.0);
});

test('deleteInterview sends DELETE and receives confirmation', async () => {
  let capturedUrl = '';
  let capturedMethod = '';

  globalThis.fetch = async (input, init) => {
    capturedUrl = input.toString();
    capturedMethod = init?.method || 'GET';
    return new Response(
      JSON.stringify({ success: true, message: 'Deleted session' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  };

  const res = await deleteInterview('s-1');
  assert.equal(capturedUrl, `${API_BASE_URL}/api/interview/s-1`);
  assert.equal(capturedMethod, 'DELETE');
  assert.equal(res.success, true);
});
