from pyrogram import Client
from pytgcalls import PyTgCalls

from config import API_ID, API_HASH, BOT_TOKEN, SESSION_SECRET

bot = Client(
    "copy_music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

assistant = Client(
    "copy_music_assistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_SECRET,
    in_memory=True,
)

voice = PyTgCalls(assistant)
