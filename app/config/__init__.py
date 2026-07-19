from dotenv import load_dotenv
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "nvidia"
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "deepseek-ai/deepseek-v4-pro"
)

NVIDIA_API_KEY = os.getenv(
    "NVIDIA_API_KEY"
)

if NVIDIA_API_KEY:
    print("✅ NVIDIA API KEY loaded")
else:
    print("❌ NVIDIA API KEY missing")

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

if not SESSION_SECRET_KEY:
    SESSION_SECRET_KEY = secrets.token_hex(32)
    print("⚠️  SESSION_SECRET_KEY not set in .env — using a temporary random key (sessions will reset on restart).")