
import os
from pathlib import Path

from dotenv import load_dotenv
from gnani.stt import GnaniSTTClient

# Load the secret from backend/.env
project_root = Path(__file__).resolve().parent.parent
env_file = project_root / "backend" / ".env"
audio_file = project_root / "backend" / "prisma-test.wav"

load_dotenv(env_file)

# Check that the key exists without displaying it
if not os.getenv("GNANI_API_KEY"):
    raise RuntimeError(
        "GNANI_API_KEY is missing. Check backend/.env"
    )

if not audio_file.exists():
    raise FileNotFoundError(f"Audio file not found: {audio_file}")

print("Connecting to Gnani Prisma...")

# The SDK reads GNANI_API_KEY from the environment
client = GnaniSTTClient()

result = client.transcribe(
    str(audio_file),
    language_code="en-IN"
)

print("\nPrisma transcription result:")
print(result["transcript"])
