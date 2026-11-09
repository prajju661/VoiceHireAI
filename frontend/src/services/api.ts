/**
 * API service for communicating with the VoiceHire AI FastAPI backend.
 */

// Read backend base URL from Vite environment variable with fallback
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

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
