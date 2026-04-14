from __future__ import annotations

from pathlib import Path

APP_NAME = "MXXR Shop Bot"
DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_DATA_DIR = Path("data")
DEFAULT_DATABASE_PATH = DEFAULT_DATA_DIR / "bot.sqlite3"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_EMBED_COLOR = "#386bff"
DEFAULT_EMBED_FOOTER = "MXXR • Official FiveM Store"
TRANSCRIPTS_DIR = DEFAULT_DATA_DIR / "transcripts"
SOCIAL_PLATFORMS = ("youtube", "x", "tiktok")
MAX_POLL_OPTIONS = 5
MAX_GIVEAWAY_WINNERS = 20
