"""
Core configuration settings for VoiceHire AI backend.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables are loaded from backend/.env or root .env
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()


class Settings:
    """Application settings and environment configuration."""

    PROJECT_NAME: str = "VoiceHire AI"
    VERSION: str = "0.2.0"

    # CORS Allowed Origins
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Audio Upload Constraints
    MAX_AUDIO_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB max upload
    ALLOWED_AUDIO_EXTENSIONS: set[str] = {
        ".flac",
        ".ogg",
        ".mp3",
        ".wav",
        ".aac",
        ".m4a",
    }
    DEFAULT_LANGUAGE_CODE: str = "en-IN"

    @property
    def gnani_api_key(self) -> str:
        """Retrieve the Gnani API key from the environment without exposing it."""
        return os.getenv("GNANI_API_KEY", "")


settings = Settings()
