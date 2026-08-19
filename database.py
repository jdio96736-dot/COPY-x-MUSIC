import sqlite3
from threading import Lock
from config import DB_PATH

_lock = Lock()

def init_db():
    with _lock, sqlite3.connect(DB_PATH) as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS favourites (
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            thumbnail TEXT DEFAULT '',
            duration INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now')),
            UNIQUE(user_id, url)
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS history (
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            thumbnail TEXT DEFAULT '',
            duration INTEGER DEFAULT 0,
            played_at INTEGER DEFAULT (strftime('%s','now'))
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER PRIMARY KEY,
            autoplay INTEGER DEFAULT 1,
            loop INTEGER DEFAULT 0
        )
        """)
        db.commit()

def add_favourite(user_id, track):
    with _lock, sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT OR IGNORE INTO favourites(user_id,title,url,thumbnail,duration) VALUES(?,?,?,?,?)",
            (user_id, track.title, track.url, track.thumbnail, track.duration),
        )
        db.commit()

def remove_favourite(user_id, url):
    with _lock, sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM favourites WHERE user_id=? AND url=?", (user_id, url))
        db.commit()

def favourites(user_id):
    with _lock, sqlite3.connect(DB_PATH) as db:
        return db.execute(
            "SELECT title,url,thumbnail,duration FROM favourites WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

def add_history(user_id, track):
    with _lock, sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO history(user_id,title,url,thumbnail,duration) VALUES(?,?,?,?,?)",
            (user_id, track.title, track.url, track.thumbnail, track.duration),
        )
        db.execute("""
            DELETE FROM history
            WHERE user_id=? AND rowid NOT IN (
                SELECT rowid FROM history WHERE user_id=? ORDER BY played_at DESC LIMIT 50
            )
        """, (user_id, user_id))
        db.commit()

def get_setting(chat_id, name, default=1):
    with _lock, sqlite3.connect(DB_PATH) as db:
        row = db.execute(f"SELECT {name} FROM settings WHERE chat_id=?", (chat_id,)).fetchone()
        return default if row is None else bool(row[0])

def set_setting(chat_id, name, value):
    if name not in {"autoplay", "loop"}:
        raise ValueError("Unsupported setting")
    with _lock, sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT autoplay, loop FROM settings WHERE chat_id=?", (chat_id,)
        ).fetchone()
        autoplay = 1 if row is None else int(row[0])
        loop = 0 if row is None else int(row[1])
        if name == "autoplay":
            autoplay = int(bool(value))
        else:
            loop = int(bool(value))
        db.execute(
            "INSERT INTO settings(chat_id,autoplay,loop) VALUES(?,?,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET autoplay=excluded.autoplay, loop=excluded.loop",
            (chat_id, autoplay, loop),
        )
        db.commit()

def history(user_id):
    with _lock, sqlite3.connect(DB_PATH) as db:
        return db.execute(
            "SELECT title,url,thumbnail,duration,played_at FROM history WHERE user_id=? ORDER BY played_at DESC LIMIT 20",
            (user_id,),
        ).fetchall()
