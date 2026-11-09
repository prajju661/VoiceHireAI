/**
 * API service for communicating with the VoiceHire AI FastAPI backend.
 */

// Read backend base URL from Vite environment variable with fallback
export const API_BASE_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) ||
  'http://127.0.0.1:8000';

export interface HealthResponse {
  status: string;
  application: string;
}

export interface WelcomeResponse {
  message: string;
  application?: string;
  docs_url?: string;
}

export interface TranscribeResponse {
  success: boolean;
  transcript: string;
  language_code: string;
  provider: string;
}

/**
 * Checks the operational health of the FastAPI backend.
 * Calls GET /health.
 *
 * @throws Error if the HTTP request fails or server returns an error code.
 */
export async function checkBackendHealth(): Promise<HealthResponse> {
  const url = `${API_BASE_URL}/health`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(
        `Backend responded with HTTP status ${response.status}: ${response.statusText}`
      );
    }

    const data: HealthResponse = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(`Failed to reach backend at ${url}: ${error.message}`, {
        cause: error,
      });
    }
    throw new Error(`Failed to reach backend at ${url}: Unknown error`, {
      cause: error,
    });
  }
}

/**
 * Fetches the backend root welcome message.
 * Calls GET /.
 *
 * @throws Error if the HTTP request fails or server returns an error code.
 */
export async function getBackendWelcome(): Promise<WelcomeResponse> {
  const url = `${API_BASE_URL}/`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(
        `Backend responded with HTTP status ${response.status}: ${response.statusText}`
      );
    }

    const data: WelcomeResponse = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(`Failed to reach backend at ${url}: ${error.message}`, {
        cause: error,
      });
    }
    throw new Error(`Failed to reach backend at ${url}: Unknown error`, {
      cause: error,
    });
  }
}

/**
 * Uploads an audio file to the FastAPI backend for Gnani Prisma STT transcription.
 * Calls POST /api/speech/transcribe.
 *
 * @param audioFile The local audio file to transcribe (.wav, .mp3, .ogg, .flac, .aac, .m4a)
 * @param languageCode BCP-47 language code (defaults to 'en-IN')
 * @returns TranscribeResponse containing the recognized transcript and metadata
 */
export async function transcribeAudio(
  audioFile: File,
  languageCode: string = 'en-IN'
): Promise<TranscribeResponse> {
  const url = `${API_BASE_URL}/api/speech/transcribe`;
  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('language_code', languageCode);

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = `Server error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          errorMessage =
            typeof errorData.detail === 'string'
              ? errorData.detail
              : JSON.stringify(errorData.detail);
        }
      } catch {
        // Fallback to HTTP status text if body is not JSON
      }
      throw new Error(errorMessage);
    }

    const data: TranscribeResponse = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(error.message, { cause: error });
    }
    throw new Error('An unexpected error occurred during audio transcription.', {
      cause: error,
    });
  }
}

// =============================================================================
// Text-to-Speech — Gnani Timbre v3.0
// =============================================================================

/** Supported TTS voice options (Phase 4B: Riyaa only). */
export type TTSVoice = 'Riyaa';

/** Supported TTS language codes (en-IN and te-IN verified against backend). */
export type TTSLanguageCode = 'en-IN' | 'te-IN';

/** Request body for POST /api/speech/synthesize. */
export interface SynthesizeRequest {
  /** Text to synthesize (1–800 characters). */
  text: string;
  /** Voice name. Default: 'Riyaa'. */
  voice?: TTSVoice;
  /** BCP-47 language code. Default: 'en-IN'. */
  language_code?: TTSLanguageCode;
  /** Speed multiplier (0.0 exclusive – 3.0 inclusive). Default: 1.0. */
  speed?: number;
}

/**
 * Synthesize text into binary WAV audio via Gnani Timbre v3.0.
 *
 * Calls POST /api/speech/synthesize on the FastAPI backend.
 * The API key is kept entirely server-side — it is never present in
 * this function or any frontend environment variable.
 *
 * @param request  Synthesis parameters (text, voice, language_code, speed).
 * @returns        A Blob of type audio/wav ready for browser playback.
 * @throws         Error with a human-readable message on network or server failure.
 */
export async function synthesizeSpeech(request: SynthesizeRequest): Promise<Blob> {
  const url = `${API_BASE_URL}/api/speech/synthesize`;

  const body: SynthesizeRequest = {
    voice: 'Riyaa',
    language_code: 'en-IN',
    speed: 1.0,
    ...request,
  };

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'audio/wav',
      },
      body: JSON.stringify(body),
    });
  } catch (networkError: unknown) {
    const msg =
      networkError instanceof Error ? networkError.message : 'Network request failed.';
    throw new Error(
      `Unable to reach the speech synthesis service. Please check that the backend is running. (${msg})`,
      { cause: networkError }
    );
  }

  if (!response.ok) {
    // Try to parse a structured error detail from the backend JSON error body
    let detail = `Speech synthesis failed (HTTP ${response.status}: ${response.statusText}).`;
    try {
      const errorBody = await response.json();
      if (errorBody?.detail) {
        detail =
          typeof errorBody.detail === 'string'
            ? errorBody.detail
            : JSON.stringify(errorBody.detail);
      }
    } catch {
      // Not JSON — keep the HTTP status message
    }
    throw new Error(detail);
  }

  const blob = await response.blob();

  if (!blob || blob.size === 0) {
    throw new Error('Speech synthesis service returned empty audio. Please try again.');
  }

  return blob;
}

// =============================================================================
// Adaptive Interview Engine — Types & Schemas
// =============================================================================

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced';

export type InterviewLanguage = 'en-IN' | 'te-IN' | 'te-en';

export type JobRole =
  | 'Python Developer'
  | 'Java Developer'
  | 'Full Stack Developer'
  | 'Data Analyst';

export interface InterviewQuestion {
  question_id: string;
  question_text: string;
  role: string;
  category: string;
  difficulty: DifficultyLevel;
  language: InterviewLanguage;
  expected_concepts?: string[];
}

export interface AnswerEvaluation {
  score: number;
  is_relevant: boolean;
  strengths: string[];
  improvement_areas: string[];
  feedback: string;
  evidence_from_answer: string[];
  recommended_difficulty: DifficultyLevel;
  identified_concepts?: string[];
  missing_concepts?: string[];
}

export interface StartInterviewRequest {
  job_role: string;
  language?: InterviewLanguage;
  initial_difficulty?: DifficultyLevel;
  candidate_name?: string | null;
  candidate_email?: string | null;
}

export interface StartInterviewResponse {
  session_id: string;
  candidate_name: string | null;
  candidate_email: string | null;
  job_role: string;
  language: string;
  current_difficulty: string;
  status: string;
  reasoning_provider: string;
  first_question: InterviewQuestion;
  turn_number: number;
  created_at: string;
}

export interface SubmitAnswerRequest {
  answer_text: string;
}

export interface SubmitAnswerResponse {
  session_id: string;
  turn_number: number;
  score: number;
  feedback: string;
  strengths: string[];
  improvement_areas: string[];
  evidence_from_answer: string[];
  next_question: InterviewQuestion;
  updated_difficulty: string;
  session_status: string;
}

export interface InterviewTurnRecord {
  id: string;
  session_id: string;
  turn_number: number;
  question_id: string;
  question_text: string;
  question_category: string;
  question_difficulty: string;
  question_language: string;
  answer_text: string | null;
  score: number | null;
  feedback: string | null;
  strengths: string[];
  improvement_areas: string[];
  evidence_from_answer: string[];
  created_at: string;
  answered_at: string | null;
}

export interface InterviewSessionDetails {
  session_id: string;
  candidate_name: string | null;
  candidate_email: string | null;
  job_role: string;
  language: string;
  current_difficulty: string;
  status: string;
  reasoning_provider: string;
  overall_score: number | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  turns_count: number;
  turns: InterviewTurnRecord[];
}

export interface InterviewSummary {
  overall_score: number;
  category_scores: Record<string, number>;
  strengths: string[];
  improvement_areas: string[];
  recommendations: string[];
  questions_answered: number;
  reasoning_provider: string;
  final_difficulty: DifficultyLevel;
}

export interface SessionSummaryItem {
  id: string;
  job_role: string;
  language: string;
  difficulty: string;
  status: string;
  reasoning_provider: string;
  overall_score: number | null;
  candidate_name: string | null;
  candidate_email: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface SessionListResponse {
  total: number;
  limit: number;
  offset: number;
  sessions: SessionSummaryItem[];
}

export interface DeleteSessionResponse {
  success: boolean;
  message: string;
}

// =============================================================================
// Helper: Extract JSON Error Details
// =============================================================================

async function extractErrorDetail(
  response: Response,
  fallbackMessage: string
): Promise<string> {
  try {
    const errorBody = await response.json();
    if (errorBody && errorBody.detail) {
      return typeof errorBody.detail === 'string'
        ? errorBody.detail
        : JSON.stringify(errorBody.detail);
    }
  } catch {
    // Non-JSON response
  }
  return `${fallbackMessage} (HTTP ${response.status}: ${response.statusText})`;
}

// =============================================================================
// Adaptive Interview Engine — API Client Functions
// =============================================================================

/**
 * Initializes a new adaptive interview session on the backend.
 * Calls POST /api/interview/start.
 */
export async function startInterview(
  request: StartInterviewRequest
): Promise<StartInterviewResponse> {
  const url = `${API_BASE_URL}/api/interview/start`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const detail = await extractErrorDetail(response, 'Failed to start interview');
      throw new Error(detail);
    }

    const data: StartInterviewResponse = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(error.message, { cause: error });
    }
    throw new Error('An unexpected error occurred while starting the interview.', {
      cause: error,
    });
  }
}

/**
 * Submits the candidate's answer for the active question.
 * Evaluates the response, updates difficulty, and returns the next question.
 * Calls POST /api/interview/{session_id}/answer.
 */
export async function submitAnswer(
  sessionId: string,
  request: SubmitAnswerRequest
): Promise<SubmitAnswerResponse> {
  const url = `${API_BASE_URL}/api/interview/${encodeURIComponent(sessionId)}/answer`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const detail = await extractErrorDetail(response, 'Failed to evaluate answer');
      throw new Error(detail);
    }

    const data: SubmitAnswerResponse = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(error.message, { cause: error });
    }
    throw new Error('An unexpected error occurred while submitting the answer.', {
      cause: error,
    });
  }
}

/**
 * Retrieves comprehensive session details, turns, running scores, and state.
 * Calls GET /api/interview/{session_id}.
 */
export async function getInterviewSession(
  sessionId: string
): Promise<InterviewSessionDetails> {
  const url = `${API_BASE_URL}/api/interview/${encodeURIComponent(sessionId)}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const detail = await extractErrorDetail(
        response,
        'Failed to retrieve interview session'
      );
      throw new Error(detail);
    }

    const data: InterviewSessionDetails = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(error.message, { cause: error });
    }
    throw new Error('An unexpected error occurred while retrieving session details.', {
      cause: error,
    });
  }
}

/**
 * Concludes the interview, computes overall score, and generates the final summary report.
 * Calls POST /api/interview/{session_id}/complete.
 */
export async function completeInterview(
  sessionId: string
): Promise<InterviewSummary> {
  const url = `${API_BASE_URL}/api/interview/${encodeURIComponent(sessionId)}/complete`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const detail = await extractErrorDetail(
        response,
        'Failed to complete interview'
      );
      throw new Error(detail);
    }

    const data: InterviewSummary = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(error.message, { cause: error });
    }
    throw new Error('An unexpected error occurred while completing the interview.', {
      cause: error,
    });
  }
}

/**
 * Fetches a paginated list of recent interview sessions.
 * Calls GET /api/interview.
 */
export async function listInterviews(
  limit: number = 20,
  offset: number = 0
): Promise<SessionListResponse> {
  const url = `${API_BASE_URL}/api/interview?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const detail = await extractErrorDetail(response, 'Failed to list interviews');
      throw new Error(detail);
    }

    const data: SessionListResponse = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(error.message, { cause: error });
    }
    throw new Error('An unexpected error occurred while listing interviews.', {
      cause: error,
    });
  }
}

/**
 * Deletes an interview session and its cascading child turns.
 * Calls DELETE /api/interview/{session_id}.
 */
export async function deleteInterview(
  sessionId: string
): Promise<DeleteSessionResponse> {
  const url = `${API_BASE_URL}/api/interview/${encodeURIComponent(sessionId)}`;

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const detail = await extractErrorDetail(
        response,
        'Failed to delete interview session'
      );
      throw new Error(detail);
    }

    const data: DeleteSessionResponse = await response.json();
    return data;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw new Error(error.message, { cause: error });
    }
    throw new Error('An unexpected error occurred while deleting the session.', {
      cause: error,
    });
  }
}
