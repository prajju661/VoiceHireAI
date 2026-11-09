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
