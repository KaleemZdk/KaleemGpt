"""Central configuration: paths and environment-driven settings.

Everything the app writes lives under DATA_DIR / UPLOAD_DIR so that the
Docker volumes (/app/data, /app/uploads) persist all state across deploys.
"""

import os
from pathlib import Path

import certifi
from dotenv import load_dotenv

load_dotenv()

# Some corporate / minimal environments ship without a usable CA bundle.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
# Kept inside DATA_DIR so the vector index survives container redeploys.
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", DATA_DIR / "chroma_db")).resolve()

for _d in (DATA_DIR, UPLOAD_DIR, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'chatbot_memory.db'}"
CHECKPOINT_DB = DATA_DIR / "langgarph_checkpoints.sqlite"

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
# How many past messages are sent to the LLM each turn (keeps latency and cost flat).
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "40"))


def has_env(name: str) -> bool:
    return bool(os.getenv(name, "").strip())
