"""
Unit tests for the VoiceHire AI TTS (text-to-speech) endpoint and service.

Tests are fully mocked — no real Gnani credits are consumed.

Coverage:
  1.  Successful WAV response (service level)
  2.  Successful English synthesis (endpoint level)
  3.  Successful Telugu synthesis (endpoint level)
  4.  Empty text — validation
  5.  Text exceeding 800 characters — validation
  6.  Unsupported voice — 400
  7.  Unsupported language — 400
  8.  Missing API key — 503
  9.  Provider 403 Forbidden
  10. Provider 429 Rate Limit
  11. Provider 500 / 503 server error
  12. Timeout
  13. Invalid or empty audio response (bad WAV header)
"""

import struct
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure 'app' is resolvable from the backend directory
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException

from app.api.speech import SynthesizeRequest, synthesize_speech
from app.services.tts_service import (
    TTSAuthenticationError,
    TTSInvalidAudioError,
    TTSPermissionError,
    TTSProviderError,
    TTSRateLimitError,
    TTSServiceError,
    TTSTimeoutError,
    TTSValidationError,
    fix_wav_sizes,
    is_valid_wav_header,
    synthesize_speech_audio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def build_minimal_wav(sample_rate: int = 48000, num_samples: int = 480) -> bytes:
    """Build a syntactically valid minimal WAV binary for use in tests."""
    data_size = num_samples * 2  # 16-bit mono
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_size))  # overall chunk size
    header.extend(b"WAVEfmt ")
    header.extend(struct.pack("<I", 16))              # sub-chunk size
    header.extend(struct.pack("<H", 1))               # PCM
    header.extend(struct.pack("<H", 1))               # mono
    header.extend(struct.pack("<I", sample_rate))     # sample rate
    header.extend(struct.pack("<I", sample_rate * 2)) # byte rate
    header.extend(struct.pack("<H", 2))               # block align
    header.extend(struct.pack("<H", 16))              # bits per sample
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))
    header.extend(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return bytes(header)


SAMPLE_WAV = build_minimal_wav()
TEST_TEXT = "Hello, this is a VoiceHire AI synthesis test."


def make_request(
    text: str = TEST_TEXT,
    voice: str = "Riyaa",
    language_code: str = "en-IN",
    speed: float = 1.0,
) -> SynthesizeRequest:
    """Build a SynthesizeRequest for direct route function testing."""
    return SynthesizeRequest(
        text=text,
        voice=voice,
        language_code=language_code,
        speed=speed,
    )


# =============================================================================
# 1. WAV header validator unit tests
# =============================================================================
class TestIsValidWavHeader:
    def test_accepts_valid_wav(self):
        assert is_valid_wav_header(SAMPLE_WAV) is True

    def test_rejects_empty_bytes(self):
        assert is_valid_wav_header(b"") is False

    def test_rejects_too_short(self):
        assert is_valid_wav_header(b"RIFF\x00\x00\x00\x00WAVE") is False

    def test_rejects_non_riff(self):
        bad = bytearray(SAMPLE_WAV)
        bad[:4] = b"JUNK"
        assert is_valid_wav_header(bytes(bad)) is False

    def test_rejects_non_wave(self):
        bad = bytearray(SAMPLE_WAV)
        bad[8:12] = b"AIFF"
        assert is_valid_wav_header(bytes(bad)) is False


# =============================================================================
# 2. fix_wav_sizes unit tests
# =============================================================================
def build_streaming_wav(num_samples: int = 480, sample_rate: int = 48000) -> bytes:
    """
    Build a WAV with streaming-style 0xFFFFFFFF placeholder sizes,
    exactly as returned by Gnani Timbre v3.0.
    """
    import struct
    data_bytes = num_samples * 2        # 16-bit mono
    buf = bytearray()
    buf.extend(b"RIFF")
    buf.extend(struct.pack("<I", 0xFFFFFFFF))  # placeholder RIFF size
    buf.extend(b"WAVEfmt ")
    buf.extend(struct.pack("<I", 16))           # fmt chunk size
    buf.extend(struct.pack("<H", 1))            # PCM
    buf.extend(struct.pack("<H", 1))            # mono
    buf.extend(struct.pack("<I", sample_rate))  # sample rate
    buf.extend(struct.pack("<I", sample_rate * 2))
    buf.extend(struct.pack("<H", 2))
    buf.extend(struct.pack("<H", 16))           # 16-bit
    buf.extend(b"data")
    buf.extend(struct.pack("<I", 0xFFFFFFFF))   # placeholder data size
    buf.extend(struct.pack(f"<{num_samples}h", *([1234] * num_samples)))
    return bytes(buf)


STREAMING_WAV = build_streaming_wav(num_samples=480, sample_rate=48000)


class TestFixWavSizes:
    """Tests for the fix_wav_sizes() helper that patches streaming WAV placeholders."""

    def test_patches_riff_size(self):
        """RIFF size field (bytes 4-7) must equal total_length - 8 after patching."""
        import struct
        fixed = fix_wav_sizes(STREAMING_WAV)
        riff_size = struct.unpack_from("<I", fixed, 4)[0]
        assert riff_size == len(fixed) - 8, (
            f"Expected RIFF size {len(fixed) - 8}, got {riff_size}"
        )

    def test_patches_data_size(self):
        """data chunk size field (bytes 40-43) must equal the audio payload length."""
        import struct
        fixed = fix_wav_sizes(STREAMING_WAV)
        data_size = struct.unpack_from("<I", fixed, 40)[0]
        expected = len(fixed) - 44       # 44-byte standard header
        assert data_size == expected, f"Expected data size {expected}, got {data_size}"

    def test_riff_size_not_placeholder(self):
        """RIFF size must not be 0xFFFFFFFF after patching."""
        import struct
        fixed = fix_wav_sizes(STREAMING_WAV)
        riff_size = struct.unpack_from("<I", fixed, 4)[0]
        assert riff_size != 0xFFFFFFFF

    def test_data_size_not_placeholder(self):
        """data chunk size must not be 0xFFFFFFFF after patching."""
        import struct
        fixed = fix_wav_sizes(STREAMING_WAV)
        data_size = struct.unpack_from("<I", fixed, 40)[0]
        assert data_size != 0xFFFFFFFF

    def test_pcm_format_preserved(self):
        """Audio format field must remain PCM (1) after patching."""
        import struct
        fixed = fix_wav_sizes(STREAMING_WAV)
        audio_fmt = struct.unpack_from("<H", fixed, 20)[0]
        assert audio_fmt == 1, f"Expected PCM(1), got {audio_fmt}"

    def test_sample_rate_preserved(self):
        """Sample rate must remain 48000 Hz after patching."""
        import struct
        fixed = fix_wav_sizes(STREAMING_WAV)
        sample_rate = struct.unpack_from("<I", fixed, 24)[0]
        assert sample_rate == 48000

    def test_channels_preserved(self):
        """Channel count must remain 1 (mono) after patching."""
        import struct
        fixed = fix_wav_sizes(STREAMING_WAV)
        channels = struct.unpack_from("<H", fixed, 22)[0]
        assert channels == 1

    def test_audio_samples_preserved(self):
        """Sample data after the 44-byte header must be byte-identical before and after."""
        fixed = fix_wav_sizes(STREAMING_WAV)
        assert fixed[44:] == STREAMING_WAV[44:], "Audio samples must not be altered"

    def test_wave_module_reads_valid_duration(self):
        """Python's wave module must report a realistic positive duration."""
        import io, wave
        fixed = fix_wav_sizes(STREAMING_WAV)
        with wave.open(io.BytesIO(fixed), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
        assert frames > 0
        assert rate == 48000
        duration = frames / rate
        assert duration > 0.0, f"Duration must be > 0, got {duration}"

    def test_already_valid_wav_unchanged_sizes(self):
        """A WAV with correct sizes should not have them altered (idempotent)."""
        import struct
        correct = fix_wav_sizes(SAMPLE_WAV)
        riff_size = struct.unpack_from("<I", correct, 4)[0]
        assert riff_size == len(correct) - 8

    def test_too_short_returned_unchanged(self):
        """Input shorter than 44 bytes is returned as-is without raising."""
        short = b"RIFF\xff\xff\xff\xffWAVE"
        result = fix_wav_sizes(short)
        assert result == short

    def test_non_riff_returned_unchanged(self):
        """Non-RIFF data is returned as-is without raising."""
        junk = b"JUNK" + b"\x00" * 40
        result = fix_wav_sizes(junk)
        assert result == junk

    def test_empty_bytes_returned_unchanged(self):
        """Empty bytes are returned as-is without raising."""
        result = fix_wav_sizes(b"")
        assert result == b""


# =============================================================================
# 3. Service returns size-fixed WAV (integration of fix_wav_sizes in service)
# =============================================================================
class TestServiceReturnsSizeFixedWav:
    """Verify that synthesize_speech_audio() automatically fixes streaming WAV sizes."""

    def _run_with_streaming_wav(self, num_samples: int = 480) -> bytes:
        streaming = build_streaming_wav(num_samples=num_samples)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = streaming
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        return synthesize_speech_audio(TEST_TEXT, http_client=mock_client)

    def test_service_fixes_riff_size(self):
        import struct
        result = self._run_with_streaming_wav()
        riff_size = struct.unpack_from("<I", result, 4)[0]
        assert riff_size == len(result) - 8
        assert riff_size != 0xFFFFFFFF

    def test_service_fixes_data_size(self):
        import struct
        result = self._run_with_streaming_wav()
        data_size = struct.unpack_from("<I", result, 40)[0]
        assert data_size == len(result) - 44
        assert data_size != 0xFFFFFFFF

    def test_service_wave_module_reads_positive_duration(self):
        import io, wave
        result = self._run_with_streaming_wav(num_samples=4800)
        with wave.open(io.BytesIO(result), "rb") as w:
            duration = w.getnframes() / w.getframerate()
        assert duration > 0.0

    def test_service_invalid_audio_still_raises(self):
        """Empty / non-WAV responses must still raise TTSInvalidAudioError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b""
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        with pytest.raises(TTSInvalidAudioError):
            synthesize_speech_audio(TEST_TEXT, http_client=mock_client)


# =============================================================================
# 4. Service-layer unit tests (httpx mocked via injected client)
# =============================================================================
class TestSynthesizeSpeechAudioService:
    """Service-level unit tests with mocked httpx client."""

    def _make_mock_response(self, status_code: int = 200, content: bytes = SAMPLE_WAV):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.content = content
        return mock_resp

    def _run(self, text: str, status_code: int = 200, content: bytes = SAMPLE_WAV, **kwargs):
        mock_resp = self._make_mock_response(status_code, content)
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        return synthesize_speech_audio(text, http_client=mock_client, **kwargs)

    def test_success_returns_wav_bytes(self):
        """Service returns binary WAV bytes on a successful 200 response."""
        result = self._run(TEST_TEXT)
        assert result == SAMPLE_WAV
        assert isinstance(result, bytes)
        assert is_valid_wav_header(result)

    def test_success_english(self):
        """Service synthesizes English text without errors."""
        result = self._run(TEST_TEXT, language_code="en-IN")
        assert is_valid_wav_header(result)

    def test_success_telugu(self):
        """Service accepts Telugu language code te-IN."""
        result = self._run("నమస్కారం", language_code="te-IN", voice="Riyaa")
        assert is_valid_wav_header(result)

    def test_missing_api_key(self):
        """Missing API key raises TTSAuthenticationError."""
        with patch("app.services.tts_service.settings") as mock_settings:
            mock_settings.gnani_api_key = ""
            mock_settings.TTS_SUPPORTED_VOICES = {"Riyaa"}
            mock_settings.TTS_SUPPORTED_LANGUAGES = {"en-IN", "te-IN"}
            mock_settings.TTS_MAX_TEXT_LENGTH = 800
            mock_settings.TTS_DEFAULT_MODEL = "timbre-v3.0"
            mock_settings.TTS_DEFAULT_VOICE = "Riyaa"
            mock_settings.TTS_DEFAULT_LANGUAGE = "en-IN"
            mock_settings.TTS_ENDPOINT_URL = "https://api.vachana.ai/api/v1/tts/inference"
            mock_settings.TTS_TIMEOUT_SECONDS = 30.0
            with pytest.raises(TTSAuthenticationError):
                synthesize_speech_audio(TEST_TEXT)

    def test_provider_403(self):
        """HTTP 403 from provider raises TTSPermissionError."""
        with pytest.raises(TTSPermissionError):
            self._run(TEST_TEXT, status_code=403, content=b"Forbidden")

    def test_provider_429(self):
        """HTTP 429 from provider raises TTSRateLimitError."""
        with pytest.raises(TTSRateLimitError):
            self._run(TEST_TEXT, status_code=429, content=b"Too Many Requests")

    def test_provider_500(self):
        """HTTP 500 from provider raises TTSProviderError."""
        with pytest.raises(TTSProviderError):
            self._run(TEST_TEXT, status_code=500, content=b"Internal Server Error")

    def test_provider_503(self):
        """HTTP 503 from provider raises TTSProviderError."""
        with pytest.raises(TTSProviderError):
            self._run(TEST_TEXT, status_code=503, content=b"Service Unavailable")

    def test_timeout(self):
        """Network timeout raises TTSTimeoutError."""
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(TTSTimeoutError):
            synthesize_speech_audio(TEST_TEXT, http_client=mock_client)

    def test_empty_response(self):
        """Empty response body raises TTSInvalidAudioError."""
        with pytest.raises(TTSInvalidAudioError):
            self._run(TEST_TEXT, content=b"")

    def test_invalid_wav_response(self):
        """Non-WAV binary response raises TTSInvalidAudioError."""
        with pytest.raises(TTSInvalidAudioError):
            self._run(TEST_TEXT, content=b"This is not a WAV file" * 5)


# =============================================================================
# 3. Validation tests (no HTTP call needed — service raises before calling API)
# =============================================================================
class TestTTSValidation:
    def test_empty_text(self):
        with pytest.raises(TTSValidationError) as exc_info:
            synthesize_speech_audio("")
        assert "empty" in exc_info.value.message.lower()

    def test_whitespace_only_text(self):
        with pytest.raises(TTSValidationError) as exc_info:
            synthesize_speech_audio("   ")
        assert "empty" in exc_info.value.message.lower()

    def test_text_too_long(self):
        with pytest.raises(TTSValidationError) as exc_info:
            synthesize_speech_audio("x" * 801)
        assert "800" in exc_info.value.message or "maximum" in exc_info.value.message.lower()

    def test_text_at_limit(self):
        """800 characters should not raise a validation error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = SAMPLE_WAV
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        result = synthesize_speech_audio("a" * 800, http_client=mock_client)
        assert is_valid_wav_header(result)

    def test_unsupported_voice(self):
        with pytest.raises(TTSValidationError) as exc_info:
            synthesize_speech_audio(TEST_TEXT, voice="UnknownVoice")
        assert "voice" in exc_info.value.message.lower()

    def test_unsupported_language(self):
        with pytest.raises(TTSValidationError) as exc_info:
            synthesize_speech_audio(TEST_TEXT, language_code="fr-FR")
        assert "language" in exc_info.value.message.lower()


# =============================================================================
# 4. Endpoint-level tests — call route function directly (no TestClient)
#    Consistent with the approach used in test_speech.py.
# =============================================================================
class TestSynthesizeEndpoint:
    """
    Integration tests at the route function layer.
    The TTS service is mocked so no real API calls are made.
    """

    _PATCH_TARGET = "app.api.speech.synthesize_speech_audio"

    def test_endpoint_success_english(self):
        """Route returns a Response with audio/wav content for English text."""
        with patch(self._PATCH_TARGET, return_value=SAMPLE_WAV):
            response = synthesize_speech(make_request(text=TEST_TEXT, language_code="en-IN"))
        assert response.status_code == 200
        assert response.media_type == "audio/wav"
        assert is_valid_wav_header(response.body)

    def test_endpoint_success_telugu(self):
        """Route returns a Response with audio/wav content for Telugu text."""
        with patch(self._PATCH_TARGET, return_value=SAMPLE_WAV):
            response = synthesize_speech(make_request(text="నమస్కారం", language_code="te-IN"))
        assert response.status_code == 200
        assert response.media_type == "audio/wav"
        assert is_valid_wav_header(response.body)

    def test_endpoint_uses_defaults(self):
        """Route forwards defaults voice/language/speed to the service."""
        with patch(self._PATCH_TARGET, return_value=SAMPLE_WAV) as mock_synth:
            synthesize_speech(make_request())
        call_kwargs = mock_synth.call_args[1]
        assert call_kwargs.get("voice") == "Riyaa"
        assert call_kwargs.get("language_code") == "en-IN"
        assert call_kwargs.get("speed") == 1.0

    def test_endpoint_empty_text_pydantic(self):
        """SynthesizeRequest rejects empty text via Pydantic min_length."""
        with pytest.raises(Exception):
            # Pydantic V2 raises ValidationError for empty string with min_length=1
            SynthesizeRequest(text="", voice="Riyaa", language_code="en-IN", speed=1.0)

    def test_endpoint_text_too_long_pydantic(self):
        """SynthesizeRequest rejects text > 800 chars via Pydantic max_length."""
        with pytest.raises(Exception):
            SynthesizeRequest(text="x" * 801, voice="Riyaa", language_code="en-IN", speed=1.0)

    def test_endpoint_unsupported_voice_400(self):
        """Route raises HTTPException 400 when service raises TTSValidationError for voice."""
        with patch(self._PATCH_TARGET, side_effect=TTSValidationError("Unsupported voice 'Ghost'.")):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request(voice="Ghost"))
        assert exc_info.value.status_code == 400
        assert "voice" in exc_info.value.detail.lower()

    def test_endpoint_unsupported_language_400(self):
        """Route raises HTTPException 400 when service raises TTSValidationError for language."""
        with patch(self._PATCH_TARGET, side_effect=TTSValidationError("Unsupported language 'fr-FR'.")):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request(language_code="fr-FR"))
        assert exc_info.value.status_code == 400
        assert "language" in exc_info.value.detail.lower()

    def test_endpoint_missing_api_key_503(self):
        """Route raises HTTPException 503 when API key is not configured."""
        with patch(self._PATCH_TARGET, side_effect=TTSAuthenticationError()):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request())
        assert exc_info.value.status_code == 503

    def test_endpoint_provider_403(self):
        """Route raises HTTPException 403 when provider denies permission."""
        with patch(self._PATCH_TARGET, side_effect=TTSPermissionError()):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request())
        assert exc_info.value.status_code == 403

    def test_endpoint_provider_429(self):
        """Route raises HTTPException 429 when provider rate limits."""
        with patch(self._PATCH_TARGET, side_effect=TTSRateLimitError()):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request())
        assert exc_info.value.status_code == 429

    def test_endpoint_provider_500(self):
        """Route raises HTTPException 502 on upstream provider 5xx error."""
        with patch(self._PATCH_TARGET, side_effect=TTSProviderError()):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request())
        assert exc_info.value.status_code == 502

    def test_endpoint_timeout_504(self):
        """Route raises HTTPException 504 on request timeout."""
        with patch(self._PATCH_TARGET, side_effect=TTSTimeoutError()):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request())
        assert exc_info.value.status_code == 504

    def test_endpoint_invalid_audio_502(self):
        """Route raises HTTPException 502 when provider returns invalid audio."""
        with patch(self._PATCH_TARGET, side_effect=TTSInvalidAudioError()):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request())
        assert exc_info.value.status_code == 502

    def test_endpoint_no_api_key_in_response(self):
        """API key must never appear in any error response detail."""
        import os
        api_key = os.getenv("GNANI_API_KEY", "test-secret-key-99999")
        with patch(self._PATCH_TARGET, side_effect=TTSAuthenticationError()):
            with pytest.raises(HTTPException) as exc_info:
                synthesize_speech(make_request())
        assert api_key not in exc_info.value.detail

    def test_endpoint_content_disposition_header(self):
        """Successful response must include the filename in Content-Disposition."""
        with patch(self._PATCH_TARGET, return_value=SAMPLE_WAV):
            response = synthesize_speech(make_request())
        assert "content-disposition" in {k.lower(): v for k, v in response.headers.items()}
        cd_header = {k.lower(): v for k, v in response.headers.items()}["content-disposition"]
        assert "voicehire-tts.wav" in cd_header

