import asyncio
import os
import random
import time

from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from clients import assistant, voice
from config import DOWNLOAD_DIR, MAX_QUEUE, PROGRESS_UPDATE_SECONDS
from database import add_history, get_setting
from ui import player_text, music_keyboard
import state
from youtube import download_audio, search

try:
    from pyrogram.errors import FloodWait
except Exception:
    FloodWait = Exception

_join_locks = {}

async def ensure_assistant_in_group(bot_client, chat_id):
    try:
        me = await assistant.get_me()
        member = await bot_client.get_chat_member(chat_id, me.id)
        if str(member.status).lower() not in {"left", "kicked"}:
            return True

        try:
            invite = await bot_client.export_chat_invite_link(chat_id)
        except Exception:
            invite = (await bot_client.create_chat_invite_link(chat_id)).invite_link

        await assistant.join_chat(invite)
        return True
    except Exception:
        return False

async def ensure_voice(bot_client, chat_id):
    if not await ensure_assistant_in_group(bot_client, chat_id):
        return False, "I couldn't add the assistant to this group."
    try:
        # PyTgCalls joins the active voice chat when play() is called.
        return True, "ready"
    except Exception:
        return False, "Assistant is not ready."

async def cleanup_file(path):
    if path:
        try:
            os.remove(path)
        except OSError:
            pass

async def play_current(bot_client, chat_id):
    st = state.states.setdefault(chat_id, state.ChatState())
    async with st.lock:
        if not st.queue:
            st.current = None
            return

        track = st.queue[0]

        # Auto-join happens before download so failures are visible immediately.
        ok, reason = await ensure_assistant_in_group(bot_client, chat_id)
        if not ok:
            raise RuntimeError(reason)

        if not track.file_path or not os.path.exists(track.file_path):
            path = await download_audio(track)
            if not path:
                raise RuntimeError("YouTube download failed. Try another song/link.")
            track.file_path = path

        # PyTgCalls accepts local media paths and joins the call when necessary.
        await voice.play(chat_id, track.file_path)

        st.current = track
        st.started_at = time.time()
        st.paused_at = 0
        state.stats["plays"] += 1
        add_history(track.requested_by_id, track)

        if st.progress_task:
            st.progress_task.cancel()
        st.progress_task = asyncio.create_task(progress_loop(bot_client, chat_id))

async def progress_loop(bot_client, chat_id):
    while True:
        await asyncio.sleep(PROGRESS_UPDATE_SECONDS)
        st = state.states.get(chat_id)
        if not st or not st.current or not st.last_player_message_id:
            return
        try:
            await bot_client.edit_message_text(
                chat_id,
                st.last_player_message_id,
                player_text(chat_id),
                parse_mode=ParseMode.HTML,
                reply_markup=music_keyboard(chat_id),
            )
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" in str(e):
                continue
            return

async def queue_next(bot_client, chat_id):
    st = state.states.get(chat_id)
    if not st or not st.queue:
        return

    finished = st.queue.pop(0)
    if finished.file_path:
        await cleanup_file(finished.file_path)
        finished.file_path = ""

    if st.loop and finished:
        st.queue.insert(0, finished)
    elif st.autoplay and finished:
        try:
            related = await search(f"{finished.title} {finished.uploader}")
            for item in related:
                if item.get("url") and item["url"] != finished.url:
                    st.queue.append(state.Track(
                        title=item["title"],
                        url=item["url"],
                        duration=item.get("duration", 0),
                        thumbnail=item.get("thumbnail", ""),
                        uploader=item.get("uploader", "YouTube"),
                        views=item.get("views", 0),
                        requested_by="AutoPlay",
                        requested_by_id=finished.requested_by_id,
                    ))
                    break
        except Exception:
            pass

    if st.queue:
        try:
            await play_current(bot_client, chat_id)
        except Exception:
            if st.queue:
                st.queue.pop(0)
            if st.queue:
                await play_current(bot_client, chat_id)
    else:
        st.current = None

async def add_track(bot_client, message, result):
    chat_id = message.chat.id
    st = state.states.setdefault(chat_id, state.ChatState())
    if len(st.queue) >= MAX_QUEUE:
        raise RuntimeError(f"Queue limit reached ({MAX_QUEUE}).")

    track = state.Track(
        title=result["title"],
        url=result["url"],
        duration=result.get("duration", 0),
        thumbnail=result.get("thumbnail", ""),
        uploader=result.get("uploader", "YouTube"),
        views=result.get("views", 0),
        requested_by=message.from_user.first_name if message.from_user else "Unknown",
        requested_by_id=message.from_user.id if message.from_user else 0,
    )
    st.queue.append(track)

    if st.current is None:
        await play_current(bot_client, chat_id)
        return True
    return False

async def recover_chat(bot_client, chat_id):
    st = state.states.get(chat_id)
    if not st or not st.current:
        return
    try:
        await asyncio.sleep(3)
        await voice.reconnect()
    except Exception:
        try:
            await play_current(bot_client, chat_id)
        except Exception:
            pass

def shuffle_queue(chat_id):
    st = state.states.get(chat_id)
    if not st or len(st.queue) <= 2:
        return
    current = st.queue[0]
    rest = st.queue[1:]
    random.shuffle(rest)
    st.queue[:] = [current] + rest
