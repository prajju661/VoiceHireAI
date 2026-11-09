"""
Core configuration settings for VoiceHire AI backend.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables are loaded from backend/.env or root .env
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

DEFAULT_DATABASE_PATH = PROJECT_ROOT / "storage" / "voicehire.db"
DEFAULT_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def parse_allowed_origins(raw: str | None = None) -> list[str]:
    """
    Parse comma-separated origins, trim whitespace, and ignore empty entries.

    Falls back to local development defaults if missing, empty, or whitespace-only.
    Wildcard origins are not permitted.
    """
    if raw is None:
        raw = os.getenv("ALLOWED_ORIGINS", "")
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if "*" in parsed:
        raise ValueError("Wildcard origin ('*') is not allowed in ALLOWED_ORIGINS.")
    return parsed if parsed else list(DEFAULT_ALLOWED_ORIGINS)


class Settings:
    """Application settings and environment configuration."""

    PROJECT_NAME: str = "VoiceHire AI"
    VERSION: str = "0.2.0"

    # CORS Allowed Origins (configurable via ALLOWED_ORIGINS env var)
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return parse_allowed_origins()

    # Database Configuration (SQLite)
    DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))

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

    # Text-to-Speech (Gnani Timbre v3.0) Configuration
    TTS_ENDPOINT_URL: str = "https://api.vachana.ai/api/v1/tts/inference"
    TTS_DEFAULT_MODEL: str = "timbre-v3.0"
    TTS_DEFAULT_VOICE: str = "Riyaa"
    TTS_DEFAULT_LANGUAGE: str = "en-IN"
    TTS_SUPPORTED_VOICES: set[str] = {"Riyaa"}
    TTS_SUPPORTED_LANGUAGES: set[str] = {"en-IN", "te-IN"}
    TTS_MAX_TEXT_LENGTH: int = 800
    TTS_TIMEOUT_SECONDS: float = 30.0

    @property
    def gnani_api_key(self) -> str:
        """Retrieve the Gnani API key from the environment without exposing it."""
        return os.getenv("GNANI_API_KEY", "")


settings = Settings()
