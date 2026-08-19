import os
from pathlib import Path

def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing Replit Secret: {name}")
    return value

API_ID = int(required("API_ID"))
API_HASH = required("API_HASH")
BOT_TOKEN = required("TELEGRAM_BOT_TOKEN")
SESSION_SECRET = required("SESSION_SECRET")

APP_NAME = "Copy x Music"
VERSION = "5.0.0"

# Non-secret public links used by the UI.
CHANNEL_URL = "https://t.me/CopymusicOfficial"
SUPPORT_URL = "https://t.me/CopymusicOfficial"

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DOWNLOAD_DIR = DATA_DIR / "downloads"
DB_PATH = DATA_DIR / "music.sqlite3"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_QUEUE = 100
MAX_DOWNLOAD_MB = 120
SEARCH_CACHE_TTL = 300
PROGRESS_UPDATE_SECONDS = 8
MAX_CONCURRENT_DOWNLOADS = 2

YTDLP_BASE = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "extract_flat": False,
    "skip_download": True,
    "format": "bestaudio/best",
    "remote_components": ["ejs:github"],
    "js_runtimes": ["deno"],
}
