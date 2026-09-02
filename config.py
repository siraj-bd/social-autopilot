import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

env_filename = os.getenv("ENV_FILE", ".env")
load_dotenv(BASE_DIR / env_filename, override=True)

# Logging setup: console stdout + rolling file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "autopilot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("SocialAutopilot")


def get_bengali_font_path() -> str:
    """Find and return an installed Bengali font for macOS and Linux."""
    candidate_paths = [
        # macOS Fonts
        "/System/Library/Fonts/KohinoorBangla.ttc",
        "/Library/Fonts/kalpurush.ttf",
        "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc",
        "/System/Library/Fonts/Supplemental/Bangla MN.ttc",
        "/Library/Fonts/Siyamrupali.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        # Linux Fonts
        "/usr/share/fonts/truetype/kalpurush/kalpurush.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            logger.debug(f"Using font: {p}")
            return p

    # Fallback to default sans-serif font
    return "Arial"


def get_active_persona() -> str:
    """Determine whether the active profile is 'personal' or 'company'."""
    explicit = os.getenv("PROFILE_TYPE", "").strip().lower()
    if explicit in ["personal", "company"]:
        return explicit

    author_urn = os.getenv("LINKEDIN_AUTHOR_URN", "")
    if "organization" in author_urn:
        return "company"
    if "person" in author_urn:
        return "personal"

    env_file = os.getenv("ENV_FILE", "").lower()
    if "company" in env_file:
        return "company"
    return "personal"


@dataclass
class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
    GEMINI_TOP_P: float = float(os.getenv("GEMINI_TOP_P", "0.85"))
    PROFILE_TYPE: str = get_active_persona()
    META_PAGE_ID: str = os.getenv("META_PAGE_ID", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    INSTAGRAM_ACCOUNT_ID: str = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
    LINKEDIN_AUTHOR_URN: str = os.getenv("LINKEDIN_AUTHOR_URN", "")
    LINKEDIN_ACCESS_TOKEN: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    TTS_VOICE: str = os.getenv("DEFAULT_TTS_VOICE", "bn-BD-PradeepNeural")
    FONT_PATH: str = get_bengali_font_path()


settings = Settings()

