"""
Manual integration test for Gnani Timbre v3.0 TTS.

Run this script directly — it is NOT part of the automated pytest suite.
It makes a real HTTP request to the Gnani Timbre API and consumes credits.

Usage:
    python backend/test_timbre.py           (from project root)
    python test_timbre.py                   (from backend/ directory)

What it does:
    1. Loads backend settings (and therefore GNANI_API_KEY from backend/.env).
    2. Synthesises the VoiceHire AI introduction sentence.
    3. Saves the result to backend/timbre-test.wav.
    4. Verifies the file has a valid RIFF/WAVE header.
    5. Prints path, size, model, voice, and language — NEVER the API key.
"""

import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — work from both the project root and from backend/
# ---------------------------------------------------------------------------
_this_file = Path(__file__).resolve()
_backend_dir = _this_file.parent if _this_file.parent.name == "backend" else _this_file.parent / "backend"
_project_root = _backend_dir.parent

# Add backend directory to sys.path so 'app' is importable
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Load .env from backend/.env before importing settings
from dotenv import load_dotenv
_env_file = _backend_dir / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()  # fall back to any .env in cwd or parents

from app.core.config import settings
from app.services.tts_service import (
    is_valid_wav_header,
    synthesize_speech_audio,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_PATH = _backend_dir / "timbre-test.wav"

TEST_SENTENCE = (
    "Welcome to VoiceHire AI. "
    "Let's begin your technical interview. "
    "Please introduce yourself and tell me about your strongest technical skills."
)

VOICE = settings.TTS_DEFAULT_VOICE          # Riyaa
LANGUAGE = settings.TTS_DEFAULT_LANGUAGE    # en-IN
MODEL = settings.TTS_DEFAULT_MODEL          # timbre-v3.0

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
def preflight() -> None:
    """Verify required configuration before making a live API call."""
    if not settings.gnani_api_key or not settings.gnani_api_key.strip():
        print("[ERROR] GNANI_API_KEY is not set in backend/.env")
        sys.exit(1)
    print("[OK] GNANI_API_KEY is configured (not printed for security).")
    print(f"[OK] Endpoint : {settings.TTS_ENDPOINT_URL}")
    print(f"[OK] Model    : {MODEL}")
    print(f"[OK] Voice    : {VOICE}")
    print(f"[OK] Language : {LANGUAGE}")
    print(f"[OK] Text     : {len(TEST_SENTENCE)} characters")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    preflight()

    print("Calling Gnani Timbre v3.0 API ...")
    try:
        audio_bytes = synthesize_speech_audio(
            text=TEST_SENTENCE,
            voice=VOICE,
            language_code=LANGUAGE,
            speed=1.0,
        )
    except Exception as exc:
        print(f"[FAILED] TTS call raised {type(exc).__name__}: {exc}")
        sys.exit(1)

    # Validate WAV header
    if not is_valid_wav_header(audio_bytes):
        print("[FAILED] Response does not contain a valid RIFF/WAVE header.")
        sys.exit(1)

    # Save to disk
    OUTPUT_PATH.write_bytes(audio_bytes)

    # Verify file on disk
    if not OUTPUT_PATH.exists():
        print(f"[FAILED] Output file was not created at {OUTPUT_PATH}")
        sys.exit(1)

    file_size = OUTPUT_PATH.stat().st_size

    # Confirm WAV header from disk copy
    with OUTPUT_PATH.open("rb") as fh:
        header_on_disk = fh.read(44)
    if not is_valid_wav_header(header_on_disk):
        print("[FAILED] File on disk does not have a valid WAV header.")
        sys.exit(1)

    # Success report
    print("[SUCCESS] Gnani Timbre v3.0 integration test passed.")
    print()
    print(f"  Output file  : {OUTPUT_PATH}")
    print(f"  File size    : {file_size:,} bytes  ({file_size / 1024:.1f} KB)")
    print(f"  Model        : {MODEL}")
    print(f"  Voice        : {VOICE}")
    print(f"  Language     : {LANGUAGE}")
    print()
    print("Play the file to verify audio quality before frontend integration.")


if __name__ == "__main__":
    main()

