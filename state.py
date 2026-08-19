import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Track:
    title: str
    url: str
    stream_url: str = ""
    duration: int = 0
    thumbnail: str = ""
    uploader: str = ""
    views: int = 0
    requested_by: str = ""
    requested_by_id: int = 0
    file_path: str = ""
    source: str = "YouTube"
    position: int = 0

@dataclass
class ChatState:
    queue: list[Track] = field(default_factory=list)
    current: Optional[Track] = None
    started_at: float = 0.0
    paused_at: float = 0.0
    loop: bool = False
    autoplay: bool = True
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    progress_task: Optional[asyncio.Task] = None
    last_player_message_id: int = 0
    reconnect_task: Optional[asyncio.Task] = None

states: dict[int, ChatState] = {}
search_cache: dict[str, tuple[float, list[dict]]] = {}
stats = {
    "commands": 0,
    "plays": 0,
    "searches": 0,
    "errors": 0,
    "started": time.time(),
}
