"""
Speech-to-Text service module for VoiceHire AI.

Encapsulates provider-specific speech transcription logic using the verified
Gnani Prisma SDK (gnani-vachana) interface.
"""

import logging
from pathlib import Path
from typing import Any

from gnani.stt import GnaniSTTClient, SUPPORTED_LANGUAGES
from gnani.stt.exceptions import (
    APIError,
    AuthenticationError,
    GnaniSTTError,
    InvalidAudioError,
)
from requests.exceptions import RequestException, Timeout

from app.core.config import settings

logger = logging.getLogger(__name__)


class STTServiceError(Exception):
    """Base exception for transcription service errors."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class STTAuthenticationError(STTServiceError):
    """Raised when provider credentials are missing or invalid."""

    def __init__(
        self,
        message: str = "Speech service credentials are not configured or invalid.",
    ):
        super().__init__(message, status_code=503)


class STTInvalidAudioError(STTServiceError):
    """Raised when audio format or content is rejected."""

    def __init__(
        self,
        message: str = "The uploaded audio file is invalid or unsupported.",
    ):
        super().__init__(message, status_code=400)


class STTProviderError(STTServiceError):
    """Raised when the external STT provider fails."""

    def __init__(
        self,
        message: str = "Speech recognition service encountered an upstream error.",
    ):
        super().__init__(message, status_code=502)


class STTTimeoutError(STTServiceError):
    """Raised when the transcription request times out."""

    def __init__(
        self,
        message: str = "Speech recognition request timed out. Please try again.",
    ):
        super().__init__(message, status_code=504)


def transcribe_audio_file(
    file_path: Path,
    language_code: str = "en-IN",
) -> dict[str, Any]:
    """
    Transcribe a local audio file using Gnani Prisma STT.

    Parameters
    ----------
    file_path : Path
        Path to the local audio file to transcribe.
    language_code : str
        BCP-47 language code (e.g. 'en-IN', 'te-IN'). Defaults to 'en-IN'.

    Returns
    -------
    dict[str, Any]
        Structured transcription response:
        {
            "success": True,
            "transcript": "...",
            "language_code": "en-IN",
            "provider": "gnani_prisma"
        }

    Raises
    ------
    STTAuthenticationError
        If the Gnani API key is missing or rejected.
    STTInvalidAudioError
        If the audio format or parameters are invalid.
    STTProviderError
        If the upstream Gnani API responds with an error.
    STTTimeoutError
        If the network request times out.
    STTServiceError
        If an unexpected error occurs.
    """
    # 1. Validate file existence
    if not file_path.exists():
        raise STTInvalidAudioError("Audio file was not found on the server.")

    # 2. Validate language code
    normalized_lang = language_code.strip()
    if normalized_lang not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES.keys()))
        raise STTInvalidAudioError(
            f"Unsupported language code '{language_code}'. Supported: {supported}"
        )

    # 3. Validate credentials existence without exposing secret
    if not settings.gnani_api_key:
        logger.error("STT transcription requested but GNANI_API_KEY is not configured.")
        raise STTAuthenticationError(
            "Speech recognition service is not configured on this server."
        )

    # 4. Instantiate GnaniSTTClient (reads GNANI_API_KEY from environment or parameter)
    try:
        client = GnaniSTTClient(api_key=settings.gnani_api_key)
    except AuthenticationError as exc:
        logger.error("GnaniSTTClient authentication initialization failed.")
        raise STTAuthenticationError(
            "Speech recognition authentication failed."
        ) from exc

    # 5. Call verified SDK transcribe method
    try:
        logger.info(
            "Calling Gnani Prisma STT: language_code=%s",
            normalized_lang,
        )
        result = client.transcribe(
            str(file_path),
            language_code=normalized_lang,
        )
    except AuthenticationError as exc:
        logger.error("Gnani API authentication failure during transcription.")
        raise STTAuthenticationError(
            "Speech recognition provider rejected authentication credentials."
        ) from exc
    except InvalidAudioError as exc:
        logger.warning("Gnani rejected audio format: %s", exc)
        raise STTInvalidAudioError(
            "The audio format was rejected by the speech recognition provider."
        ) from exc
    except APIError as exc:
        logger.error("Gnani API returned HTTP %s", exc.status_code)
        raise STTProviderError(
            "Speech recognition service returned an upstream processing error."
        ) from exc
    except Timeout as exc:
        logger.error("Gnani STT request timed out.")
        raise STTTimeoutError() from exc
    except RequestException as exc:
        logger.error("Network error reaching Gnani STT API: %s", type(exc).__name__)
        raise STTProviderError(
            "Unable to communicate with speech recognition provider."
        ) from exc
    except ValueError as exc:
        logger.warning("Invalid parameter for Gnani STT: %s", exc)
        raise STTInvalidAudioError(
            "Invalid parameters provided for speech transcription."
        ) from exc
    except GnaniSTTError as exc:
        logger.error("Gnani STT error: %s", type(exc).__name__)
        raise STTProviderError(
            "Speech recognition service encountered an error."
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error in STT service: %s", type(exc).__name__)
        raise STTServiceError(
            "An unexpected error occurred during audio transcription."
        ) from exc

    # 6. Extract transcript safely
    transcript = result.get("transcript", "") if isinstance(result, dict) else ""

    return {
        "success": True,
        "transcript": transcript,
        "language_code": normalized_lang,
        "provider": "gnani_prisma",
    }
