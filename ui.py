import html
import time
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import APP_NAME, CHANNEL_URL, SUPPORT_URL, VERSION
import state

def esc(text):
    return html.escape(str(text or ""))

def duration(seconds):
    seconds = int(seconds or 0)
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"

def bar(current, total, width=12):
    if total <= 0:
        return "▱" * width
    pos = max(0, min(width - 1, int(current / total * width)))
    return "".join("▰" if i <= pos else "▱" for i in range(width))

def welcome_text(first_name, username):
    return (
        f"👋 <b>Hey {esc(first_name)}!</b>\n\n"
        f"🎵 <b>{APP_NAME}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎧 High quality Voice Chat music\n"
        f"⚡ YouTube + yt-dlp search\n"
        f"🤖 Auto assistant join & recovery\n"
        f"📚 Queue • Favorites • History\n"
        f"🎛 Live player controls\n\n"
        f"💡 <i>Use /play &lt;song name&gt; in a group.</i>"
    )

def home_keyboard(username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{username}?startgroup=true")],
        [
            InlineKeyboardButton("📜 Help", callback_data="help"),
            InlineKeyboardButton("🎵 Music", callback_data="music"),
        ],
        [
            InlineKeyboardButton("📢 Channel", url=CHANNEL_URL),
            InlineKeyboardButton("💬 Support", url=SUPPORT_URL),
        ],
        [InlineKeyboardButton(f"v{VERSION}", callback_data="about")],
    ])

def help_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Music", callback_data="music")],
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
    ])

def music_keyboard(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data=f"pause:{chat_id}"),
            InlineKeyboardButton("▶️ Resume", callback_data=f"resume:{chat_id}"),
        ],
        [
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip:{chat_id}"),
            InlineKeyboardButton("⏹ Stop", callback_data=f"stop:{chat_id}"),
        ],
        [
            InlineKeyboardButton("📜 Queue", callback_data=f"queue:{chat_id}"),
            InlineKeyboardButton("🔄 Loop", callback_data=f"loop:{chat_id}"),
        ],
    ])

def player_text(chat_id):
    st = state.states.get(chat_id)
    if not st or not st.current:
        return "🎵 <b>No song is playing.</b>"
    t = st.current
    elapsed = 0 if st.paused_at else max(0, time.time() - st.started_at)
    if st.paused_at:
        elapsed = st.paused_at - st.started_at
    return (
        f"🎧 <b>NOW PLAYING</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎵 <b>{esc(t.title)}</b>\n"
        f"👤 Requested by: {esc(t.requested_by)}\n"
        f"⏱ {duration(elapsed)} {bar(elapsed, t.duration)} {duration(t.duration)}\n"
        f"👀 Views: <code>{t.views:,}</code>\n"
        f"📡 Source: <b>{esc(t.source)}</b>\n"
        f"📚 Queue: <code>{len(st.queue)}</code>"
    )
