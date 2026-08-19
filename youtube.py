import asyncio
import time
from urllib.parse import urlparse

import yt_dlp

from config import YTDLP_BASE, DOWNLOAD_DIR, SEARCH_CACHE_TTL
import state

def _is_url(text: str) -> bool:
    try:
        return urlparse(text).scheme in {"http", "https"}
    except Exception:
        return False

def _extract(query: str, flat: bool = False):
    opts = dict(YTDLP_BASE)
    opts["extract_flat"] = flat
    opts["skip_download"] = True
    target = query if _is_url(query) else f"ytsearch8:{query}"
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(target, download=False)

async def search(query: str) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    now = time.time()
    cached = state.search_cache.get(query.lower())
    if cached and now - cached[0] < SEARCH_CACHE_TTL:
        return cached[1]

    state.stats["searches"] += 1
    try:
        info = await asyncio.to_thread(_extract, query, True)
        entries = info.get("entries") if isinstance(info, dict) else None
        if not entries:
            entries = [info] if info else []

        results = []
        for item in entries[:8]:
            if not item:
                continue
            results.append({
                "title": item.get("title") or "Unknown",
                "url": item.get("webpage_url") or item.get("url") or "",
                "duration": int(item.get("duration") or 0),
                "thumbnail": item.get("thumbnail") or "",
                "uploader": item.get("uploader") or item.get("channel") or "YouTube",
                "views": int(item.get("view_count") or 0),
            })
        state.search_cache[query.lower()] = (now, results)
        return results
    except Exception:
        state.stats["errors"] += 1
        return []

async def get_info(url: str) -> dict | None:
    try:
        info = await asyncio.to_thread(_extract, url, False)
        if info.get("entries"):
            info = info["entries"][0]
        return {
            "title": info.get("title") or "Unknown",
            "url": info.get("webpage_url") or url,
            "duration": int(info.get("duration") or 0),
            "thumbnail": info.get("thumbnail") or "",
            "uploader": info.get("uploader") or info.get("channel") or "YouTube",
            "views": int(info.get("view_count") or 0),
        }
    except Exception:
        state.stats["errors"] += 1
        return None

async def download_audio(track) -> str | None:
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in track.title)[:80]
    output = DOWNLOAD_DIR / f"{safe}-{abs(hash(track.url))}.%(ext)s"

    opts = dict(YTDLP_BASE)
    opts.update({
        "noplaylist": True,
        "format": "bestaudio/best",
        "outtmpl": str(output),
        "quiet": True,
        "postprocessors": [],
    })

    try:
        await asyncio.to_thread(_download, track.url, opts)
        candidates = list(DOWNLOAD_DIR.glob(output.name.replace("%(ext)s", "*")))
        if not candidates:
            return None
        return str(candidates[0])
    except Exception:
        state.stats["errors"] += 1
        return None

def _download(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


async def get_playlist(url: str, limit: int = 25) -> list[dict]:
    def _playlist():
        opts = dict(YTDLP_BASE)
        opts.update({"noplaylist": False, "extract_flat": True, "playlistend": limit})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries") or []
            out = []
            for item in entries[:limit]:
                if not item:
                    continue
                entry_url = item.get("webpage_url") or item.get("url")
                if not entry_url:
                    vid = item.get("id")
                    if vid:
                        entry_url = f"https://www.youtube.com/watch?v={vid}"
                out.append({
                    "title": item.get("title") or "Unknown",
                    "url": entry_url or "",
                    "duration": int(item.get("duration") or 0),
                    "thumbnail": item.get("thumbnail") or "",
                    "uploader": item.get("uploader") or item.get("channel") or "YouTube",
                    "views": int(item.get("view_count") or 0),
                })
            return out
    try:
        return await asyncio.to_thread(_playlist)
    except Exception:
        state.stats["errors"] += 1
        return []
