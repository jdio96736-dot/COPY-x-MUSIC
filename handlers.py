import asyncio
import time

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database
import state
from clients import bot, assistant, voice
from config import APP_NAME, CHANNEL_URL, SUPPORT_URL, VERSION
from player import add_track, play_current, queue_next, recover_chat, shuffle_queue
from ui import welcome_text, home_keyboard, help_keyboard, music_keyboard, player_text, duration
from youtube import search, get_info, get_playlist


CONTROL_ADMIN = {"pause", "resume", "skip", "stop", "loop", "shuffle", "restart", "autoplay"}

async def is_admin(client, message):
    if not message.from_user:
        return False
    if message.chat.type == "private":
        return True
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in {ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}
    except Exception:
        return False

def command_count():
    state.stats["commands"] += 1

async def safe_reply(message, text, **kwargs):
    try:
        return await message.reply_text(text, **kwargs)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await message.reply_text(text, **kwargs)

@bot.on_message(filters.command("start"))
async def start(_, message):
    command_count()
    me = await bot.get_me()
    await message.reply_text(
        welcome_text(message.from_user.first_name if message.from_user else "there", me.username),
        parse_mode=ParseMode.HTML,
        reply_markup=home_keyboard(me.username),
    )

@bot.on_message(filters.command("help"))
async def help_cmd(_, message):
    command_count()
    text = (
        f"🎵 <b>{APP_NAME} Help</b>\n\n"
        "<b>Music</b>\n"
        "/play &lt;song&gt; — search and play\n"
        "/vplay &lt;song&gt; — play video-capable media\n"
        "/queue — show queue\n"
        "/nowplaying — current track\n"
        "/pause /resume — pause/resume\n"
        "/skip /stop — control playback\n"
        "/seek &lt;seconds&gt; — seek position\n"
        "/loop — toggle loop\n"
        "/shuffle — shuffle queue\n"
        "/autoplay — toggle related-song autoplay\n\n"
        "<b>Library</b>\n"
        "/fav — save current track\n"
        "/unfav — remove current track\n"
        "/lyrics &lt;song&gt; — lyrics lookup placeholder-free fallback\n\n"
        "<b>System</b>\n"
        "/ping /stats /restart\n\n"
        "Everyone can use <code>/play</code>. Playback-control commands are admin-only in groups."
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=help_keyboard())

@bot.on_message(filters.command(["play", "vplay"]))
async def play_cmd(_, message):
    command_count()
    query = " ".join(message.command[1:]).strip()
    if not query:
        return await message.reply_text("🎵 Usage: <code>/play song name</code>", parse_mode=ParseMode.HTML)

    status = await message.reply_text("🔎 <b>Searching YouTube…</b>", parse_mode=ParseMode.HTML)
    if "youtube.com/playlist" in query or ("list=" in query and "youtube.com" in query):
        playlist = await get_playlist(query)
        if not playlist:
            return await status.edit_text("❌ Could not read this YouTube playlist.")
        added = 0
        try:
            for item in playlist:
                class FakeMessage:
                    chat = message.chat
                    from_user = message.from_user
                started = await add_track(message._client, FakeMessage(), item)
                added += 1
                if added >= 25:
                    break
            return await status.edit_text(
                f"✅ <b>Playlist added</b>: <code>{added}</code> tracks.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            return await status.edit_text(f"❌ Playlist error: <code>{str(e)[:700]}</code>", parse_mode=ParseMode.HTML)

    results = await search(query)
    if not results:
        return await status.edit_text("❌ No YouTube result found.")

    if len(results) > 1 and not query.startswith(("http://", "https://")):
        buttons = []
        for i, r in enumerate(results[:5]):
            buttons.append([InlineKeyboardButton(
                f"{i+1}. {r['title'][:45]}",
                callback_data=f"pick:{message.chat.id}:{message.from_user.id}:{i}"
            )])
        # Cache the short result set in state.
        state.search_cache[f"pick:{message.chat.id}:{message.from_user.id}"] = (time.time(), results[:5])
        return await status.edit_text(
            "🎧 <b>Choose a result:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    try:
        started = await add_track(message._client, message, results[0])
        await status.delete()
        if not started:
            await message.reply_text(
                f"✅ <b>Added to queue</b>\n🎵 {results[0]['title']}",
                parse_mode=ParseMode.HTML
            )
        else:
            await send_player(message._client, message.chat.id, message)
    except Exception as e:
        await status.edit_text(f"❌ <b>Playback failed:</b>\n<code>{str(e)[:800]}</code>", parse_mode=ParseMode.HTML)

async def send_player(client, chat_id, source_message):
    st = state.states.get(chat_id)
    if not st or not st.current:
        return
    sent = await client.send_message(
        chat_id,
        player_text(chat_id),
        parse_mode=ParseMode.HTML,
        reply_markup=music_keyboard(chat_id),
    )
    st.last_player_message_id = sent.id

@bot.on_callback_query()
async def callbacks(_, query):
    data = query.data or ""
    await query.answer()
    if data == "home":
        me = await bot.get_me()
        return await query.message.edit_text(
            welcome_text(query.from_user.first_name, me.username),
            parse_mode=ParseMode.HTML,
            reply_markup=home_keyboard(me.username)
        )
    if data == "help":
        return await query.message.edit_text(
            "📖 <b>Commands</b>\n\n"
            "/play /vplay /pause /resume /skip /stop /queue /lyrics\n"
            "/nowplaying /ping /stats /restart /seek /loop /shuffle /autoplay\n"
            "/fav /unfav",
            parse_mode=ParseMode.HTML,
            reply_markup=help_keyboard()
        )
    if data == "music":
        return await query.message.edit_text(
            "🎵 <b>Music Controls</b>\n\nUse /play in a group to start.",
            parse_mode=ParseMode.HTML,
            reply_markup=help_keyboard()
        )
    if data == "about":
        return await query.message.edit_text(
            f"🎵 <b>{APP_NAME}</b>\nVersion <code>{VERSION}</code>\n"
            f"Pyrogram + PyTgCalls + yt-dlp",
            parse_mode=ParseMode.HTML,
            reply_markup=help_keyboard()
        )
    if data.startswith("pick:"):
        _, chat_id, user_id, index = data.split(":")
        if int(user_id) != query.from_user.id:
            return await query.answer("This search belongs to another user.", show_alert=True)
        key = f"pick:{chat_id}:{user_id}"
        cached = state.search_cache.get(key)
        if not cached or int(index) >= len(cached[1]):
            return await query.answer("Search expired. Try /play again.", show_alert=True)
        r = cached[1][int(index)]
        class Fake:
            chat = query.message.chat
            from_user = query.from_user
        try:
            started = await add_track(bot, Fake(), r)
            await query.message.edit_text(
                ("▶️ <b>Starting:</b> " if started else "✅ <b>Queued:</b> ") +
                f"{r['title']}", parse_mode=ParseMode.HTML
            )
            if started:
                await send_player(bot, query.message.chat.id, query.message)
        except Exception as e:
            await query.message.edit_text(f"❌ {str(e)[:800]}")

    if ":" in data and data.split(":")[0] in CONTROL_ADMIN:
        action, chat_id = data.split(":", 1)
        chat_id = int(chat_id)
        if not await is_admin(bot, query.message):
            return await query.answer("Admins only.", show_alert=True)
        await do_control(action, chat_id, query.message)

async def do_control(action, chat_id, message):
    st = state.states.get(chat_id)
    if action == "pause":
        await voice.pause(chat_id)
        if st: st.paused_at = time.time()
    elif action == "resume":
        await voice.resume(chat_id)
        if st and st.paused_at:
            st.started_at += time.time() - st.paused_at
            st.paused_at = 0
    elif action == "skip":
        if st and st.queue:
            await queue_next(bot, chat_id)
    elif action == "stop":
        if st:
            st.queue.clear()
            st.current = None
        try: await voice.leave_call(chat_id)
        except Exception: pass
    elif action == "loop":
        if st: st.loop = not st.loop
    elif action == "shuffle":
        shuffle_queue(chat_id)
    elif action == "autoplay":
        if st: st.autoplay = not st.autoplay
    elif action == "restart":
        await message.reply_text("♻️ Restarting is controlled by the Replit process.")
    await message.reply_text(player_text(chat_id), parse_mode=ParseMode.HTML)

@bot.on_message(filters.command("queue"))
async def queue_cmd(_, message):
    st = state.states.get(message.chat.id)
    if not st or not st.queue:
        return await message.reply_text("📭 Queue is empty.")
    lines = ["📚 <b>Queue</b>\n"]
    for i, t in enumerate(st.queue[:20], 1):
        marker = "▶️" if i == 1 else f"{i}."
        lines.append(f"{marker} {t.title[:60]} — {duration(t.duration)}")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

@bot.on_message(filters.command("nowplaying"))
async def nowplaying(_, message):
    await message.reply_text(player_text(message.chat.id), parse_mode=ParseMode.HTML, reply_markup=music_keyboard(message.chat.id))

@bot.on_message(filters.command("pause"))
async def pause(_, message):
    if await is_admin(bot, message):
        await do_control("pause", message.chat.id, message)

@bot.on_message(filters.command("resume"))
async def resume(_, message):
    if await is_admin(bot, message):
        await do_control("resume", message.chat.id, message)

@bot.on_message(filters.command("skip"))
async def skip(_, message):
    if await is_admin(bot, message):
        await do_control("skip", message.chat.id, message)

@bot.on_message(filters.command("stop"))
async def stop(_, message):
    if await is_admin(bot, message):
        await do_control("stop", message.chat.id, message)

@bot.on_message(filters.command("loop"))
async def loop(_, message):
    if await is_admin(bot, message):
        await do_control("loop", message.chat.id, message)

@bot.on_message(filters.command("shuffle"))
async def shuffle(_, message):
    if await is_admin(bot, message):
        await do_control("shuffle", message.chat.id, message)

@bot.on_message(filters.command("autoplay"))
async def autoplay(_, message):
    if await is_admin(bot, message):
        await do_control("autoplay", message.chat.id, message)

@bot.on_message(filters.command("fav"))
async def fav(_, message):
    st = state.states.get(message.chat.id)
    if not st or not st.current:
        return await message.reply_text("❌ Nothing is playing.")
    database.add_favourite(message.from_user.id, st.current)
    await message.reply_text("❤️ Added to favourites.")

@bot.on_message(filters.command("unfav"))
async def unfav(_, message):
    st = state.states.get(message.chat.id)
    if not st or not st.current:
        return await message.reply_text("❌ Nothing is playing.")
    database.remove_favourite(message.from_user.id, st.current.url)
    await message.reply_text("💔 Removed from favourites.")

@bot.on_message(filters.command("lyrics"))
async def lyrics(_, message):
    import aiohttp
    q = " ".join(message.command[1:]).strip()
    if not q:
        return await message.reply_text("Usage: /lyrics song name")
    status = await message.reply_text("🎤 <b>Searching lyrics…</b>", parse_mode=ParseMode.HTML)
    try:
        parts = q.split(" ", 1)
        artist = parts[0]
        title = parts[1] if len(parts) > 1 else q
        url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                data = await resp.json(content_type=None)
        lyric = (data.get("lyrics") or "").strip()
        if not lyric:
            return await status.edit_text("❌ Lyrics not found.")
        if len(lyric) > 3800:
            lyric = lyric[:3800] + "…"
        await status.edit_text(
            f"🎤 <b>{q}</b>\n\n<blockquote>{lyric.replace('<','&lt;').replace('>','&gt;')}</blockquote>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await status.edit_text("❌ Lyrics service is unavailable right now.")

@bot.on_message(filters.command("seek"))
async def seek(_, message):
    if not await is_admin(bot, message):
        return
    st = state.states.get(message.chat.id)
    if not st or not st.current or not st.current.file_path:
        return await message.reply_text("❌ Nothing is playing.")
    if len(message.command) < 2:
        return await message.reply_text("Usage: /seek 90")
    try:
        seconds = max(0, int(message.command[1]))
    except ValueError:
        return await message.reply_text("❌ Enter seconds, e.g. /seek 90")
    if st.current.duration and seconds >= st.current.duration:
        return await message.reply_text("❌ Seek position is past the end.")
    import subprocess, os
    src = st.current.file_path
    out = src + f".seek-{seconds}.mp3"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(seconds), "-i", src, "-vn", "-c:a", "libmp3lame", "-b:a", "192k", out],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45
        )
        await voice.play(message.chat.id, out)
        st.current.file_path = out
        st.started_at = time.time() - seconds
        st.paused_at = 0
        await message.reply_text(f"⏩ Seeked to <code>{duration(seconds)}</code>.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"❌ Seek failed: <code>{str(e)[:500]}</code>", parse_mode=ParseMode.HTML)

@bot.on_message(filters.command("ping"))
async def ping(_, message):
    start = time.perf_counter()
    m = await message.reply_text("🏓 Pinging…")
    ms = round((time.perf_counter() - start) * 1000)
    await m.edit_text(f"🏓 <b>Pong!</b> <code>{ms} ms</code>", parse_mode=ParseMode.HTML)

@bot.on_message(filters.command("stats"))
async def stats_cmd(_, message):
    up = int(time.time() - state.stats["started"])
    await message.reply_text(
        f"📊 <b>Stats</b>\n\n"
        f"Commands: <code>{state.stats['commands']}</code>\n"
        f"Plays: <code>{state.stats['plays']}</code>\n"
        f"Searches: <code>{state.stats['searches']}</code>\n"
        f"Errors: <code>{state.stats['errors']}</code>\n"
        f"Uptime: <code>{up}s</code>",
        parse_mode=ParseMode.HTML,
    )

@bot.on_message(filters.command("restart"))
async def restart(_, message):
    if not await is_admin(bot, message):
        return
    await message.reply_text("♻️ Restarting…")
    await asyncio.sleep(1)
    import os, sys
    os.execv(sys.executable, [sys.executable] + sys.argv)

# Best-effort stream-end handler for versions exposing StreamEnded.
try:
    from pytgcalls import filters as call_filters
    from pytgcalls.types import StreamEnded

    @voice.on_update(call_filters.stream_end())
    async def _stream_end(_, update: StreamEnded):
        chat_id = update.chat_id
        try:
            await queue_next(bot, chat_id)
        except Exception:
            await recover_chat(bot, chat_id)
except Exception:
    pass

# Network handler is version-dependent; recovery is also triggered from the
# playback layer on exceptions.
