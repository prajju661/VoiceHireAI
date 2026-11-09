"""
Speech API routes for VoiceHire AI backend.

Provides the speech-to-text transcription endpoint powered by Gnani Prisma.
"""

import logging
from pathlib import Path
import tempfile
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
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
