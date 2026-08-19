import asyncio
import logging
import os
import shutil

from pyrogram import idle
from pyrogram.errors import FloodWait

import database
from clients import bot, assistant, voice
import handlers  # registers bot handlers
from config import APP_NAME, VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(APP_NAME)

async def startup_checks():
    if not shutil.which("ffmpeg"):
        log.warning("ffmpeg was not found. PyTgCalls/yt-dlp playback may fail.")
    database.init_db()

async def run():
    await startup_checks()

    log.info("Starting %s %s", APP_NAME, VERSION)
    await bot.start()
    log.info("Bot started: @%s", (await bot.get_me()).username)

    try:
        await assistant.start()
        me = await assistant.get_me()
        log.info("Assistant started: @%s (%s)", me.username, me.id)

        await voice.start()
        log.info("PyTgCalls started")

        await idle()
    finally:
        try:
            await voice.stop()
        except Exception:
            pass
        try:
            await assistant.stop()
        except Exception:
            pass
        try:
            await bot.stop()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
