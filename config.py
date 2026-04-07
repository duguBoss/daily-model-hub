import os
from datetime import datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
TRENDING_URL = "https://huggingface.co/models?sort=trending"
DATA_DIR = ROOT_DIR / "data"
DAILY_DIR = DATA_DIR / "daily"
WEEK_DIR = DATA_DIR / "week"
IMAGE_ROOT_DIR = ROOT_DIR / "assets" / "huggingface_model_cards"

# 使用北京时间（UTC+8）
BEIJING_NOW = datetime.utcnow() + timedelta(hours=8)
RUN_DATE = BEIJING_NOW.date()
RUN_STAMP = RUN_DATE.strftime("%Y-%m-%d")
DAILY_OUTPUT_FILE = DAILY_DIR / f"{RUN_STAMP}.json"
RUN_IMAGE_DIR = IMAGE_ROOT_DIR / RUN_STAMP

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

MODEL_LIMIT = int(os.environ.get("HF_MODEL_LIMIT", "5") or "5")
WEEKLY_PICK_LIMIT = int(os.environ.get("HF_WEEKLY_PICK_LIMIT", "6") or "6")


def normalize_limit(value: int, fallback: int) -> int:
    return value if value > 0 else fallback


MODEL_LIMIT = normalize_limit(MODEL_LIMIT, 30)
WEEKLY_PICK_LIMIT = normalize_limit(WEEKLY_PICK_LIMIT, 6)


def ensure_dirs() -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    WEEK_DIR.mkdir(parents=True, exist_ok=True)
    RUN_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def require_gemini_api_key() -> None:
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY. This workflow requires Gemini to generate Chinese summaries.")
