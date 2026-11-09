"""
Text-to-Speech (TTS) service module for VoiceHire AI.

Encapsulates provider-specific speech synthesis logic using Gnani Timbre v3.0.
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================
class TTSServiceError(Exception):
    """Base exception for text-to-speech service errors."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class TTSValidationError(TTSServiceError):
    """Raised when request parameters fail validation."""

    def __init__(self, message: str = "Invalid input parameters for speech synthesis."):
        super().__init__(message, status_code=400)


class TTSAuthenticationError(TTSServiceError):
    """Raised when provider credentials are missing or rejected."""

    def __init__(
        self,
        message: str = "Speech synthesis service credentials are not configured or invalid.",
    ):
        super().__init__(message, status_code=503)


class TTSPermissionError(TTSServiceError):
    """Raised when the upstream provider denies access or permissions."""

    def __init__(
        self,
        message: str = "Speech synthesis permission denied by provider.",
    ):
        super().__init__(message, status_code=403)


class TTSRateLimitError(TTSServiceError):
    """Raised when provider rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Speech synthesis rate limit exceeded. Please try again later.",
    ):
        super().__init__(message, status_code=429)


class TTSProviderError(TTSServiceError):
    """Raised when the external TTS provider fails."""

    def __init__(
        self,
        message: str = "Speech synthesis service encountered an upstream provider error.",
    ):
        super().__init__(message, status_code=502)


class TTSTimeoutError(TTSServiceError):
    """Raised when the synthesis request times out."""

    def __init__(
        self,
        message: str = "Speech synthesis request timed out. Please try again.",
    ):
        super().__init__(message, status_code=504)


class TTSInvalidAudioError(TTSServiceError):
    """Raised when the provider response is not valid audio."""

    def __init__(
        self,
        message: str = "Speech synthesis provider returned an invalid or empty audio response.",
    ):
        super().__init__(message, status_code=502)


# =============================================================================
# Helper Utilities
# =============================================================================
def is_valid_wav_header(data: bytes) -> bool:
    """
    Verify that binary data begins with a valid RIFF/WAVE header.

    A valid standard WAV file begins with 'RIFF' (bytes 0-3), specifies the
    chunk size (bytes 4-7), and contains the 'WAVE' format marker (bytes 8-11),
    requiring at least 44 bytes to constitute a minimal standard header.
    """
    return (
        isinstance(data, (bytes, bytearray))
        and len(data) >= 44
        and data[:4] == b"RIFF"
        and data[8:12] == b"WAVE"
    )


def _find_chunk_offset(data: bytes, chunk_id: bytes, start: int = 12) -> int:
    """
    Scan RIFF chunks from *start* and return the byte offset of the given
    chunk's size field (i.e. the 4 bytes immediately after chunk_id), or -1
    if not found.
    """
    pos = start
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        csz = int.from_bytes(data[pos + 4:pos + 8], "little")
        if cid == chunk_id:
            return pos + 4          # offset of the size field
        pos += 8 + csz
        # Stop scanning if we hit a placeholder or walk off the end
        if csz >= 0xFFFF0000:
            break
    return -1


def fix_wav_sizes(raw: bytes) -> bytes:
    """
    Patch a WAV byte string whose RIFF and/or data chunk size fields contain
    ``0xFFFFFFFF`` placeholder values (produced by streaming encoders such as
    the Gnani Timbre v3.0 API).

    The function performs a targeted in-place rewrite of only the two 4-byte
    little-endian size fields:

    * Bytes  4– 7: RIFF chunk size  = ``total_length − 8``
    * Bytes 40–43: data chunk size  = audio sample bytes after the header

    The audio sample data itself is never modified.  If the RIFF header magic
    or the ``data`` chunk cannot be located the original bytes are returned
    unchanged so callers can still apply their own validation.

    Parameters
    ----------
    raw : bytes
        The complete WAV file bytes as received from the provider.

    Returns
    -------
    bytes
        WAV bytes with accurate size fields.
    """
    if not raw or len(raw) < 44:
        return raw
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        return raw

    buf = bytearray(raw)
    total = len(buf)

    # --- RIFF chunk size (bytes 4–7) ---
    correct_riff_size = total - 8
    buf[4:8] = correct_riff_size.to_bytes(4, "little")

    # --- data chunk size (located by scanning chunks after byte 12) ---
    # First pass: locate the data chunk offset by walking properly-sized chunks
    pos = 12
    data_size_offset = -1
    while pos + 8 <= total:
        cid = bytes(buf[pos:pos + 4])
        csz = int.from_bytes(buf[pos + 4:pos + 8], "little")
        if cid == b"data":
            data_size_offset = pos + 4
            break
        # Skip placeholder chunks (would otherwise walk off the buffer)
        if csz >= 0xFFFF0000:
            break
        pos += 8 + csz

    if data_size_offset != -1:
        # Audio payload begins right after the data chunk id+size (8 bytes)
        audio_start = data_size_offset + 4
        correct_data_size = total - audio_start
        buf[data_size_offset:data_size_offset + 4] = correct_data_size.to_bytes(4, "little")
        logger.debug(
            "Patched WAV sizes: total=%d, riff_size=%d, data_size=%d (audio_start=%d)",
            total, correct_riff_size, correct_data_size, audio_start,
        )
    else:
        logger.warning("fix_wav_sizes: could not locate 'data' chunk; RIFF size patched only.")

    return bytes(buf)


# =============================================================================
# Service Implementation
# =============================================================================
def synthesize_speech_audio(
    text: str,
    voice: str = settings.TTS_DEFAULT_VOICE,
    language_code: str = settings.TTS_DEFAULT_LANGUAGE,
    speed: float = 1.0,
    timeout: float = settings.TTS_TIMEOUT_SECONDS,
    http_client: httpx.Client | None = None,
) -> bytes:
    """
    Synthesize text into binary WAV audio using Gnani Timbre v3.0.

    Parameters
    ----------
    text : str
        Text string to synthesize (max 800 characters).
    voice : str
        Voice name (default: 'Riyaa').
    language_code : str
        BCP-47 language code (e.g. 'en-IN', 'te-IN').
    speed : float
        Playback speed multiplier (default: 1.0).
    timeout : float
        HTTP request timeout in seconds.
    http_client : httpx.Client | None
        Optional httpx.Client instance for dependency injection/testing.

    Returns
    -------
    bytes
        Raw binary WAV audio bytes.

    Raises
    ------
    TTSValidationError
        If input parameters violate constraints.
    TTSAuthenticationError
        If Gnani credentials are not configured or invalid.
    TTSPermissionError
        If provider returns 403 Forbidden.
    TTSRateLimitError
        If provider returns 429 Too Many Requests.
    TTSProviderError
        If provider returns upstream 5xx or unexpected HTTP errors.
    TTSTimeoutError
        If the HTTP request times out.
    TTSInvalidAudioError
        If provider returns empty or non-WAV response payload.
    """
    # 1. Validate text presence and length
    normalized_text = text.strip() if text else ""
    if not normalized_text:
        raise TTSValidationError("Text is required and cannot be empty.")

    if len(text) > settings.TTS_MAX_TEXT_LENGTH:
        raise TTSValidationError(
            f"Text length exceeds maximum allowed limit of {settings.TTS_MAX_TEXT_LENGTH} characters."
        )

    # 2. Validate voice
    if voice not in settings.TTS_SUPPORTED_VOICES:
        supported = ", ".join(sorted(settings.TTS_SUPPORTED_VOICES))
        raise TTSValidationError(
            f"Unsupported voice '{voice}'. Supported voices: {supported}"
        )

    # 3. Validate language code
    if language_code not in settings.TTS_SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(settings.TTS_SUPPORTED_LANGUAGES))
        raise TTSValidationError(
            f"Unsupported language '{language_code}'. Supported languages: {supported}"
        )

    # 4. Validate speed
    if speed <= 0.0 or speed > 3.0:
        raise TTSValidationError("Speed must be greater than 0 and at most 3.0.")

    # 5. Check API key configuration without leaking it
    api_key = settings.gnani_api_key
    if not api_key or not api_key.strip():
        logger.error("TTS synthesis requested but GNANI_API_KEY is not configured.")
        raise TTSAuthenticationError(
            "Speech synthesis service credentials are not configured on this server."
        )

    # 6. Prepare Timbre inference request
    headers = {
        "X-API-Key-ID": api_key,
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "text": text,
        "model": settings.TTS_DEFAULT_MODEL,
        "voice": voice,
        "language": language_code,
        "speed": float(speed),
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    logger.info(
        "Calling Gnani Timbre TTS: model=%s, voice=%s, language=%s, text_length=%d",
        settings.TTS_DEFAULT_MODEL,
        voice,
        language_code,
        len(text),
    )

    # 7. Execute HTTP request with safe error handling
    try:
        if http_client is not None:
            response = http_client.post(
                settings.TTS_ENDPOINT_URL,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        else:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    settings.TTS_ENDPOINT_URL,
                    json=payload,
                    headers=headers,
                )
    except httpx.TimeoutException as exc:
        logger.error("Gnani Timbre TTS request timed out.")
        raise TTSTimeoutError() from exc
    except httpx.RequestError as exc:
        logger.error("Network error communicating with Gnani Timbre TTS API: %s", type(exc).__name__)
        raise TTSProviderError(
            "Unable to communicate with speech synthesis provider."
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during Timbre HTTP request: %s", type(exc).__name__)
        raise TTSServiceError(
            "An unexpected error occurred during text-to-speech synthesis."
        ) from exc

    # 8. Handle HTTP status codes
    if response.status_code == 401:
        logger.error("Gnani Timbre API returned 401 Unauthorized.")
        raise TTSAuthenticationError(
            "Speech synthesis provider rejected authentication credentials."
        )
    if response.status_code == 403:
        logger.error("Gnani Timbre API returned 403 Forbidden.")
        raise TTSPermissionError(
            "Speech synthesis service permission denied by provider."
        )
    if response.status_code == 429:
        logger.error("Gnani Timbre API returned 429 Rate Limit Exceeded.")
        raise TTSRateLimitError(
            "Speech synthesis rate limit exceeded. Please try again later."
        )
    if response.status_code >= 500:
        logger.error("Gnani Timbre API returned HTTP %s server error.", response.status_code)
        raise TTSProviderError(
            f"Speech synthesis service returned an upstream provider error (HTTP {response.status_code})."
        )
    if response.status_code != 200:
        logger.error("Gnani Timbre API returned unexpected HTTP %s status.", response.status_code)
        raise TTSProviderError(
            f"Speech synthesis service returned unexpected HTTP status {response.status_code}."
        )

    # 9. Extract and validate binary WAV payload
    audio_bytes = response.content
    if not audio_bytes or len(audio_bytes) < 44:
        logger.error(
            "Gnani Timbre returned empty or truncated response (%d bytes).",
            len(audio_bytes) if audio_bytes else 0,
        )
        raise TTSInvalidAudioError(
            "Speech synthesis provider returned an invalid or empty audio response."
        )

    if not is_valid_wav_header(audio_bytes):
        logger.error("Gnani Timbre response did not contain a valid RIFF/WAVE header.")
        raise TTSInvalidAudioError(
            "Speech synthesis provider returned an invalid WAV audio response."
        )

    # 10. Fix placeholder size fields produced by Gnani's streaming encoder.
    #     Gnani Timbre returns RIFF/data sizes as 0xFFFFFFFF (streaming mode).
    #     Patch both fields to their true values so the WAV is fully valid.
    audio_bytes = fix_wav_sizes(audio_bytes)

    logger.info("Successfully received %d bytes of WAV audio from Timbre.", len(audio_bytes))
    return audio_bytes

