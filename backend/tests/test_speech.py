"""
Unit and integration tests for the VoiceHire AI speech transcription endpoint.

Tests:
1. Successful transcription with mock Gnani SDK.
2. Missing audio file rejection (400).
3. Unsupported audio format rejection (400).
4. Provider/API failure handling (502 / 503).
5. Temporary audio file cleanup on success and failure.
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.api.speech import transcribe_speech
from app.services.stt_service import (
    STTAuthenticationError,
    STTInvalidAudioError,
    STTProviderError,
    STTTimeoutError,
    transcribe_audio_file,
)
from gnani.stt.exceptions import APIError, AuthenticationError, InvalidAudioError
from requests.exceptions import Timeout


def create_mock_upload(
    filename: str = "sample.wav",
    content: bytes = b"RIFF....WAVEfmt ....data....",
) -> UploadFile:
    """Helper to create an in-memory FastAPI UploadFile."""
    return UploadFile(filename=filename, file=io.BytesIO(content))


# =====================================================================
# 1. Successful Transcription
# =====================================================================
def test_transcribe_speech_success():
    """Verify successful speech transcription with mock Gnani response."""
    mock_upload = create_mock_upload("candidate_response.wav", b"fake audio bytes")

    with patch("app.api.speech.transcribe_audio_file") as mock_stt:
        mock_stt.return_value = {
            "success": True,
            "transcript": "Hello, my name is Priya and I have 5 years of Python experience.",
            "language_code": "en-IN",
            "provider": "gnani_prisma",
        }

        response = transcribe_speech(
            audio=mock_upload,
            language_code="en-IN",
        )

        assert response.success is True
        assert (
            response.transcript
            == "Hello, my name is Priya and I have 5 years of Python experience."
        )
        assert response.language_code == "en-IN"
        assert response.provider == "gnani_prisma"
        mock_stt.assert_called_once()


def test_transcribe_speech_telugu_language():
    """Verify optional language code (e.g. te-IN) is accepted."""
    mock_upload = create_mock_upload("telugu_sample.wav", b"fake audio bytes")

    with patch("app.api.speech.transcribe_audio_file") as mock_stt:
        mock_stt.return_value = {
            "success": True,
            "transcript": "నమస్కారం, నా పేరు రాజేష్.",
            "language_code": "te-IN",
            "provider": "gnani_prisma",
        }

        response = transcribe_speech(
            audio=mock_upload,
            language_code="te-IN",
        )

        assert response.success is True
        assert response.language_code == "te-IN"
        assert response.transcript == "నమస్కారం, నా పేరు రాజేష్."


def test_transcribe_live_recorded_pcm_wav():
    """Verify live microphone 16 kHz 16-bit mono PCM WAV is accepted and processed."""
    import struct

    num_samples = 320
    data_size = num_samples * 2
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_size))
    header.extend(b"WAVEfmt ")
    header.extend(struct.pack("<I", 16))  # Subchunk1Size
    header.extend(struct.pack("<H", 1))  # PCM
    header.extend(struct.pack("<H", 1))  # Mono
    header.extend(struct.pack("<I", 16000))  # 16000 Hz
    header.extend(struct.pack("<I", 32000))  # ByteRate
    header.extend(struct.pack("<H", 2))  # BlockAlign
    header.extend(struct.pack("<H", 16))  # 16-bit
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))
    samples = struct.pack(f"<{num_samples}h", *([500] * num_samples))
    wav_payload = bytes(header + samples)

    mock_upload = create_mock_upload("voicehire-recording-1718000000.wav", wav_payload)

    with patch("app.api.speech.transcribe_audio_file") as mock_stt:
        mock_stt.return_value = {
            "success": True,
            "transcript": "I am answering the interview question with live microphone input.",
            "language_code": "en-IN",
            "provider": "gnani_prisma",
        }

        response = transcribe_speech(
            audio=mock_upload,
            language_code="en-IN",
        )

        assert response.success is True
        assert (
            response.transcript
            == "I am answering the interview question with live microphone input."
        )
        assert response.language_code == "en-IN"
        assert response.provider == "gnani_prisma"
        mock_stt.assert_called_once()


# =====================================================================
# 2. Missing Audio File
# =====================================================================
def test_transcribe_speech_missing_file():
    """Verify 400 error when no audio file is provided."""
    with pytest.raises(HTTPException) as exc_info:
        transcribe_speech(audio=None, file=None)

    assert exc_info.value.status_code == 400
    assert "audio file is required" in exc_info.value.detail.lower()


def test_transcribe_speech_empty_file():
    """Verify 400 error when an empty audio file is uploaded."""
    mock_upload = create_mock_upload("empty.wav", b"")

    with pytest.raises(HTTPException) as exc_info:
        transcribe_speech(audio=mock_upload)

    assert exc_info.value.status_code == 400
    assert "0 bytes" in exc_info.value.detail.lower() or "empty" in exc_info.value.detail.lower()


# =====================================================================
# 3. Unsupported Audio Type
# =====================================================================
def test_transcribe_speech_unsupported_audio_type():
    """Verify 400 error when an unsupported file type is uploaded."""
    mock_upload = create_mock_upload("document.pdf", b"%PDF-1.4...")

    with pytest.raises(HTTPException) as exc_info:
        transcribe_speech(audio=mock_upload)

    assert exc_info.value.status_code == 400
    assert "unsupported audio format" in exc_info.value.detail.lower()
    assert ".pdf" in exc_info.value.detail.lower()


# =====================================================================
# 4. Provider / API Failure
# =====================================================================
def test_transcribe_speech_provider_api_error():
    """Verify 502 error when Gnani API returns an upstream error."""
    mock_upload = create_mock_upload("interview.mp3", b"fake mp3 audio")

    with patch("app.api.speech.transcribe_audio_file") as mock_stt:
        mock_stt.side_effect = STTProviderError("Upstream Gnani failure")

        with pytest.raises(HTTPException) as exc_info:
            transcribe_speech(audio=mock_upload)

        assert exc_info.value.status_code == 502
        assert (
            "upstream" in exc_info.value.detail.lower()
            or "gnani" in exc_info.value.detail.lower()
        )


def test_transcribe_speech_authentication_error():
    """Verify 503 error when credentials are not configured or invalid."""
    mock_upload = create_mock_upload("interview.wav", b"fake wav audio")

    with patch("app.api.speech.transcribe_audio_file") as mock_stt:
        mock_stt.side_effect = STTAuthenticationError("Credentials missing")

        with pytest.raises(HTTPException) as exc_info:
            transcribe_speech(audio=mock_upload)

        assert exc_info.value.status_code == 503
        assert "credentials" in exc_info.value.detail.lower()


# =====================================================================
# 5. Temporary File Cleanup
# =====================================================================
def test_temporary_file_cleanup_on_success():
    """Verify temporary files are deleted after successful transcription."""
    created_temp_files = []

    def mock_service_call(file_path: Path, language_code: str = "en-IN"):
        assert file_path.exists(), "Temporary file should exist while service is processing"
        created_temp_files.append(file_path)
        return {
            "success": True,
            "transcript": "Success",
            "language_code": language_code,
            "provider": "gnani_prisma",
        }

    mock_upload = create_mock_upload("audio.wav", b"sample wav content")

    with patch("app.api.speech.transcribe_audio_file", side_effect=mock_service_call):
        transcribe_speech(audio=mock_upload)

    assert len(created_temp_files) == 1
    assert (
        not created_temp_files[0].exists()
    ), "Temporary file must be deleted after request completion"


def test_temporary_file_cleanup_on_failure():
    """Verify temporary files are cleaned up even when the service raises an exception."""
    created_temp_files = []

    def mock_service_failure(file_path: Path, language_code: str = "en-IN"):
        assert file_path.exists(), "Temporary file should exist when error triggers"
        created_temp_files.append(file_path)
        raise STTProviderError("Gnani failed mid-request")

    mock_upload = create_mock_upload("failed.wav", b"sample wav content")

    with patch("app.api.speech.transcribe_audio_file", side_effect=mock_service_failure):
        with pytest.raises(HTTPException):
            transcribe_speech(audio=mock_upload)

    assert len(created_temp_files) == 1
    assert (
        not created_temp_files[0].exists()
    ), "Temporary file must be deleted even after failure"


# =====================================================================
# 6. Service Unit Tests (Mocking GnaniSTTClient directly)
# =====================================================================
def test_stt_service_gnani_client_call():
    """Test transcribe_audio_file invokes GnaniSTTClient.transcribe correctly."""
    dummy_file = Path("dummy_test.wav")
    dummy_file.write_bytes(b"dummy")

    try:
        with patch("app.services.stt_service.settings") as mock_settings, patch(
            "app.services.stt_service.GnaniSTTClient"
        ) as MockClient:

            mock_settings.gnani_api_key = "dummy_secret_key"
            client_instance = MagicMock()
            client_instance.transcribe.return_value = {
                "success": True,
                "transcript": "Transcribed text from Prisma",
                "request_id": "req-12345",
            }
            MockClient.return_value = client_instance

            result = transcribe_audio_file(dummy_file, language_code="en-IN")

            assert result["success"] is True
            assert result["transcript"] == "Transcribed text from Prisma"
            assert result["language_code"] == "en-IN"
            assert result["provider"] == "gnani_prisma"

            MockClient.assert_called_once_with(api_key="dummy_secret_key")
            client_instance.transcribe.assert_called_once_with(
                str(dummy_file),
                language_code="en-IN",
            )
    finally:
        if dummy_file.exists():
            dummy_file.unlink()


def test_stt_service_handles_gnani_exceptions():
    """Test transcribe_audio_file maps Gnani SDK exceptions to service exceptions."""
    dummy_file = Path("dummy_error.wav")
    dummy_file.write_bytes(b"dummy")

    try:
        with patch("app.services.stt_service.settings") as mock_settings, patch(
            "app.services.stt_service.GnaniSTTClient"
        ) as MockClient:

            mock_settings.gnani_api_key = "valid_key"
            client_instance = MagicMock()
            MockClient.return_value = client_instance

            # Test APIError -> STTProviderError
            client_instance.transcribe.side_effect = APIError(
                status_code=500, body="API Error"
            )
            with pytest.raises(STTProviderError):
                transcribe_audio_file(dummy_file)

            # Test AuthenticationError -> STTAuthenticationError
            client_instance.transcribe.side_effect = AuthenticationError("Auth error")
            with pytest.raises(STTAuthenticationError):
                transcribe_audio_file(dummy_file)

            # Test InvalidAudioError -> STTInvalidAudioError
            client_instance.transcribe.side_effect = InvalidAudioError("Bad audio")
            with pytest.raises(STTInvalidAudioError):
                transcribe_audio_file(dummy_file)

            # Test Timeout -> STTTimeoutError
            client_instance.transcribe.side_effect = Timeout("Timeout")
            with pytest.raises(STTTimeoutError):
                transcribe_audio_file(dummy_file)
    finally:
        if dummy_file.exists():
            dummy_file.unlink()
