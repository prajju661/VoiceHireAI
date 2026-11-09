"""
Speech API routes for VoiceHire AI backend.

Provides:
- POST /api/speech/transcribe  — speech-to-text via Gnani Prisma
- POST /api/speech/synthesize  — text-to-speech via Gnani Timbre v3.0
"""

import logging
from pathlib import Path
import tempfile
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.stt_service import (
    STTAuthenticationError,
    STTInvalidAudioError,
    STTProviderError,
    STTServiceError,
    STTTimeoutError,
    transcribe_audio_file,
)
from app.services.tts_service import (
    TTSAuthenticationError,
    TTSInvalidAudioError,
    TTSPermissionError,
    TTSProviderError,
    TTSRateLimitError,
    TTSServiceError,
    TTSTimeoutError,
    TTSValidationError,
    synthesize_speech_audio,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/speech", tags=["Speech"])


class TranscribeResponse(BaseModel):
    """Schema for successful speech transcription response."""

    success: bool = Field(True, description="Whether transcription succeeded")
    transcript: str = Field(..., description="Recognized speech transcript")
    language_code: str = Field(..., description="Language code used for recognition")
    provider: str = Field("gnani_prisma", description="Underlying speech STT provider")


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    summary="Transcribe speech audio via Gnani Prisma",
    description="Upload an audio file (wav, mp3, ogg, flac, aac, m4a) to generate a text transcript.",
)
def transcribe_speech(
    audio: Annotated[
        UploadFile | None,
        File(description="Audio file to transcribe (multipart/form-data)"),
    ] = None,
    file: Annotated[
        UploadFile | None,
        File(description="Alternative form field for the audio file"),
    ] = None,
    language_code: Annotated[
        str,
        Form(description="BCP-47 language code (defaults to en-IN)"),
    ] = settings.DEFAULT_LANGUAGE_CODE,
) -> TranscribeResponse:
    """
    Transcribes an uploaded audio file using Gnani Prisma STT.

    Validates audio format and size, stages the file to a secure temporary
    location, invokes the Gnani Prisma STT service, and guarantees temporary
    file cleanup on completion or error.
    """
    upload = audio or file

    # 1. Validate that an audio file was uploaded
    if upload is None or not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An audio file is required in multipart/form-data ('audio' or 'file').",
        )

    # 2. Validate file extension against supported Gnani Prisma audio formats
    filename = upload.filename
    extension = Path(filename).suffix.lower()

    if extension not in settings.ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_AUDIO_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported audio format '{extension}'. "
                f"Supported formats: {allowed}"
            ),
        )

    # 3. Stream upload into a temporary file with size limit enforcement
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    temp_path = Path(temp_file.name)
    total_bytes = 0

    try:
        chunk_size = 1024 * 64  # 64 KB chunks
        while chunk := upload.file.read(chunk_size):
            total_bytes += len(chunk)
            if total_bytes > settings.MAX_AUDIO_SIZE_BYTES:
                max_mb = settings.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Audio file exceeds the maximum allowed size of {max_mb} MB.",
                )
            temp_file.write(chunk)

        temp_file.flush()
        temp_file.close()

        # Check for empty file
        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded audio file is empty (0 bytes).",
            )

        # 4. Perform speech transcription via service
        try:
            result = transcribe_audio_file(
                file_path=temp_path,
                language_code=language_code,
            )
            return TranscribeResponse(**result)

        except STTAuthenticationError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
            ) from exc
        except STTInvalidAudioError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
            ) from exc
        except STTTimeoutError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
            ) from exc
        except STTProviderError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
            ) from exc
        except STTServiceError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
            ) from exc
        except Exception as exc:
            logger.error("Unhandled exception during transcription: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during audio transcription.",
            ) from exc

    finally:
        # Guarantee temporary file is closed and cleaned up under all conditions
        if not temp_file.closed:
            try:
                temp_file.close()
            except OSError:
                pass

        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as err:
                logger.warning("Failed to remove temporary file %s: %s", temp_path, err)


# =============================================================================
# TTS — Text-to-Speech endpoint (Gnani Timbre v3.0)
# =============================================================================


class SynthesizeRequest(BaseModel):
    """Request schema for speech synthesis via Gnani Timbre v3.0."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=800,
        description="Text to synthesize into speech (max 800 characters).",
    )
    voice: str = Field(
        default="Riyaa",
        description="Voice name for synthesis (supported: Riyaa).",
    )
    language_code: str = Field(
        default="en-IN",
        description="BCP-47 language code for synthesis (supported: en-IN, te-IN).",
    )
    speed: float = Field(
        default=1.0,
        gt=0.0,
        le=3.0,
        description="Speech speed multiplier (0.0 exclusive – 3.0 inclusive).",
    )


@router.post(
    "/synthesize",
    summary="Synthesize speech audio via Gnani Timbre v3.0",
    description=(
        "Convert text to speech using Gnani Timbre v3.0. "
        "Returns binary WAV audio (audio/wav). "
        "Supported voices: Riyaa. Supported languages: en-IN, te-IN. "
        "Maximum text length: 800 characters."
    ),
    response_class=Response,
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "WAV audio file successfully synthesized.",
        },
        400: {"description": "Validation error — empty/too-long text, unsupported voice or language."},
        403: {"description": "Provider permission denied."},
        429: {"description": "Provider rate limit exceeded."},
        503: {"description": "Speech synthesis credentials not configured."},
        502: {"description": "Upstream provider error or invalid audio response."},
        504: {"description": "Provider request timed out."},
    },
)
def synthesize_speech(request: SynthesizeRequest) -> Response:
    """
    Synthesize text into binary WAV audio using Gnani Timbre v3.0.

    Validates input, forwards the request to the TTS service, and returns
    raw binary WAV audio. API credentials and provider details remain
    entirely server-side — they are never echoed to callers.
    """
    try:
        audio_bytes = synthesize_speech_audio(
            text=request.text,
            voice=request.voice,
            language_code=request.language_code,
            speed=request.speed,
        )
    except TTSValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except TTSAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc
    except TTSPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc
    except TTSRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
        ) from exc
    except TTSTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=exc.message,
        ) from exc
    except TTSInvalidAudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
        ) from exc
    except TTSProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
        ) from exc
    except TTSServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.error("Unhandled exception during speech synthesis: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during speech synthesis.",
        ) from exc

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'inline; filename="voicehire-tts.wav"',
            "Content-Length": str(len(audio_bytes)),
        },
    )
