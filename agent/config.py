import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _p(env: str, default: Path) -> Path:
    v = os.getenv(env)
    return (ROOT / v).resolve() if v and not os.path.isabs(v) else Path(v) if v else default


HARNESS_PATH = _p("HARNESS_PATH", ROOT / "harness" / "harness.yaml")
EVENT_LOG_PATH = _p("EVENT_LOG_PATH", ROOT / "data" / "events.sqlite")
SANDBOX_DIR = _p("SANDBOX_DIR", ROOT / "sandbox")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_PROVIDER_OVERRIDE = os.getenv("LLM_PROVIDER")  # np. "fake"
