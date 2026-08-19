import os

API_ID = int(os.getenv("API_ID", "39247548"))
API_HASH = os.getenv("API_HASH", "54496b848af8f320019f4b4d174ce935")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("ASSISTANT_SESSION") or os.getenv("STRING_SESSION")
MAIN_OWNER = int(os.getenv("OWNER_ID", "6983361101"))
DEPLOYED_OWNER_ID = int(os.getenv("OWNER_ID", "6983361101"))
SEARCH_API_URL = os.getenv("SEARCH_API_URL", "https://search-api.kustbotsweb.workers.dev")
DOWNLOAD_API_BASE = os.getenv("DOWNLOAD_API_BASE", "").rstrip("/")
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES", "")
RATE_LIMIT_COUNT = 4
RATE_LIMIT_WINDOW = 6
MAX_TITLE_LEN = 30
PORT = int(os.getenv("PORT", "8080"))
