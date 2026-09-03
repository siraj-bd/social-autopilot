import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
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
    """Find and return an installed Bengali/Unicode font for macOS and Linux."""
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


def get_tts_voice(lang: str = "en") -> str:
    """Returns optimal neural TTS voice based on target language."""
    if lang.lower() in ["bn", "bangla", "bengali"]:
        return os.getenv("DEFAULT_BENGALI_TTS_VOICE", "bn-BD-PradeepNeural")
    return os.getenv("DEFAULT_ENGLISH_TTS_VOICE", "en-US-ChristopherNeural")


@dataclass
class AccountConfig:
    key: str
    name: str
    enabled: bool
    max_characters: int
    supported_content_types: List[str]
    credentials_configured: bool
    description: str = ""


@dataclass
class Settings:
    # Language Configuration: English is system default, Bengali is optional
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en").lower()

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
    GEMINI_TOP_P: float = float(os.getenv("GEMINI_TOP_P", "0.85"))
    PROFILE_TYPE: str = get_active_persona()

    # Meta Graph API (Facebook Page & Instagram Business)
    META_PAGE_ID: str = os.getenv("META_PAGE_ID", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    INSTAGRAM_ACCOUNT_ID: str = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

    # LinkedIn REST API
    LINKEDIN_AUTHOR_URN: str = os.getenv("LINKEDIN_AUTHOR_URN", "")
    LINKEDIN_ACCESS_TOKEN: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    LINKEDIN_API_VERSION: str = os.getenv("LINKEDIN_API_VERSION", "202503")

    # Account ON/OFF Toggles (Environment-based with sensible defaults)
    ENABLE_LINKEDIN_PERSONAL: bool = os.getenv("ENABLE_LINKEDIN_PERSONAL", "true").lower() in ["true", "1", "yes"]
    ENABLE_LINKEDIN_COMPANY: bool = os.getenv("ENABLE_LINKEDIN_COMPANY", "true" if "company" in get_active_persona() else "false").lower() in ["true", "1", "yes"]
    ENABLE_FACEBOOK_PAGE: bool = os.getenv("ENABLE_FACEBOOK_PAGE", "true" if os.getenv("META_ACCESS_TOKEN") else "false").lower() in ["true", "1", "yes"]
    ENABLE_INSTAGRAM: bool = os.getenv("ENABLE_INSTAGRAM", "false").lower() in ["true", "1", "yes"]

    # Voice and Font
    TTS_VOICE: str = get_tts_voice(os.getenv("DEFAULT_LANGUAGE", "en"))
    FONT_PATH: str = get_bengali_font_path()


settings = Settings()


def get_platform_registry() -> Dict[str, AccountConfig]:
    """
    Returns the centralized platform and account registry with live
    character limits, supported media types, credentials status, and ON/OFF toggles.
    """
    has_li_token = bool(settings.LINKEDIN_ACCESS_TOKEN)
    has_li_person = bool(has_li_token and "person:" in settings.LINKEDIN_AUTHOR_URN)
    has_li_org = bool(has_li_token and "organization:" in settings.LINKEDIN_AUTHOR_URN and "<" not in settings.LINKEDIN_AUTHOR_URN)
    has_meta = bool(settings.META_PAGE_ID and settings.META_ACCESS_TOKEN)
    has_ig = bool(settings.INSTAGRAM_ACCOUNT_ID and settings.META_ACCESS_TOKEN)

    return {
        "linkedin_personal": AccountConfig(
            key="linkedin_personal",
            name="LinkedIn Personal Profile",
            enabled=settings.ENABLE_LINKEDIN_PERSONAL,
            max_characters=3000,
            supported_content_types=["text_only", "image", "video"],
            credentials_configured=has_li_person,
            description="Professional post with structured takeaways and hashtags (max 3000 chars)"
        ),
        "linkedin_company": AccountConfig(
            key="linkedin_company",
            name="LinkedIn Company Page",
            enabled=settings.ENABLE_LINKEDIN_COMPANY,
            max_characters=3000,
            supported_content_types=["text_only", "image", "video"],
            credentials_configured=has_li_org,
            description="Technical knowledge hub and company updates (max 3000 chars)"
        ),
        "facebook_page": AccountConfig(
            key="facebook_page",
            name="Facebook Page",
            enabled=settings.ENABLE_FACEBOOK_PAGE,
            max_characters=63206,
            supported_content_types=["text_only", "image", "video"],
            credentials_configured=has_meta,
            description="Conversational, community-focused post with clear line breaks (max 63206 chars)"
        ),
        "instagram": AccountConfig(
            key="instagram",
            name="Instagram Business",
            enabled=settings.ENABLE_INSTAGRAM,
            max_characters=2200,
            supported_content_types=["image", "video"],
            credentials_configured=has_ig,
            description="Visual storytelling caption with focused hashtags (max 2200 chars)"
        )
    }


def normalize_platform_keys(raw_platforms: str) -> List[str]:
    """
    Normalizes user/CSV platform strings and aliases into canonical account keys.
    e.g. 'linkedin,facebook' -> ['linkedin_personal', 'facebook_page']
    """
    tokens = [p.strip().lower() for p in raw_platforms.split(",") if p.strip()]
    canonical_keys = []
    persona = settings.PROFILE_TYPE

    for t in tokens:
        if t in ["linkedin", "li"]:
            if persona == "company":
                canonical_keys.append("linkedin_company")
            else:
                canonical_keys.append("linkedin_personal")
        elif t in ["linkedin_personal", "personal"]:
            canonical_keys.append("linkedin_personal")
        elif t in ["linkedin_company", "company", "org"]:
            canonical_keys.append("linkedin_company")
        elif t in ["facebook", "fb", "facebook_page"]:
            canonical_keys.append("facebook_page")
        elif t in ["instagram", "ig"]:
            canonical_keys.append("instagram")
        elif t in get_platform_registry():
            canonical_keys.append(t)

    # Return unique canonical keys preserving order
    seen = set()
    return [k for k in canonical_keys if not (k in seen or seen.add(k))]
