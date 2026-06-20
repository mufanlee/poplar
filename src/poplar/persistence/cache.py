"""Two-tier cache: memory LRU + SQLite persistence."""

import json
import time
import hashlib
import sqlite3
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Callable


def get_cache_db_path() -> str:
    """Get the SQLite cache database path.

    Prefers ~/.poplar/poplar.db, but falls back to the project directory
    or temp directory if filesystem is read-only.
    """
    import tempfile
    for base in (Path.home() / ".poplar", Path.cwd() / ".poplar", Path(tempfile.gettempdir()) / ".poplar"):
        try:
            base.mkdir(parents=True, exist_ok=True)
            test = base / ".write_test"
            test.touch()
            test.unlink()
            return str(base / "poplar.db")
        except (OSError, PermissionError):
            continue
    return str(Path(tempfile.mkdtemp(prefix="poplar-")) / "poplar.db")


def make_key(*parts: str) -> str:
    """Build a cache key from colon-separated parts."""
    return ":".join(parts)


def hash_messages(messages: list) -> str:
    """Deterministic hash of a message list for API cache keying."""
    raw = json.dumps(
        [{"role": m.role.value, "content": m.content,
          "tool_calls": m.tool_calls, "name": m.name}
         for m in messages],
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CacheEntry:
    """In-memory cache entry with expiry."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: str, expires_at: float):
        self.value = value
        self.expires_at = expires_at


class CacheManager:
    """Two-tier cache: fast memory LRU backed by SQLite persistence.

    Memory tier provides O(1) access for hot entries.
    SQLite tier provides durability across restarts and higher capacity.
    """

    def __init__(self, db_path: Optional[str] = None, max_memory: Optional[int] = None):
        self.db_path = db_path or get_cache_db_path()
        self.max_memory = max_memory if max_memory is not None else 100
        self._memory: OrderedDict[str, CacheEntry] = OrderedDict()
        self._init_table()

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_table(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    cache_type TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        """Get a cached value. Returns None on miss or expiry."""
        now = time.time()

        # 1. Check memory (fast path)
        entry = self._memory.get(key)
        if entry:
            if now < entry.expires_at:
                self._memory.move_to_end(key)
                return entry.value
            del self._memory[key]

        # 2. Check SQLite (slow path, promotes to memory)
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        finally:
            conn.close()

        if row:
            expires_at = row[1]
            if now < expires_at:
                value: str = row[0]
                self._put_memory(key, value, expires_at)
                return value
            # Expired — remove from DB
            self._delete_from_db(key)

        return None

    def set(self, key: str, value: str, ttl_seconds: int, cache_type: str = "generic"):
        """Store a value in both memory and SQLite."""
        now = time.time()
        expires_at = now + ttl_seconds

        self._put_memory(key, value, expires_at)
        self._upsert_db(key, value, cache_type, now, expires_at)

    def invalidate(self, pattern: str):
        """Invalidate all cache entries whose key starts with *pattern*."""
        now = time.time()

        # Remove from memory
        matched_memory = [k for k in self._memory if k.startswith(pattern)]
        for k in matched_memory:
            del self._memory[k]

        # Remove from SQLite
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM cache WHERE key LIKE ?", (pattern + "%",))
            conn.commit()
        finally:
            conn.close()

    def clear(self):
        """Clear all cached entries."""
        self._memory.clear()
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM cache")
            conn.commit()
        finally:
            conn.close()

    def get_or_compute(self, key: str, ttl_seconds: int, compute: Callable[[], str],
                       cache_type: str = "generic") -> str:
        """Get cached value or compute, store, and return it."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute()
        self.set(key, value, ttl_seconds, cache_type)
        return value

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _put_memory(self, key: str, value: str, expires_at: float):
        """Insert into memory LRU, evicting oldest if full."""
        if key in self._memory:
            self._memory.move_to_end(key)
        elif len(self._memory) >= self.max_memory:
            self._memory.popitem(last=False)
        self._memory[key] = CacheEntry(value, expires_at)

    def _upsert_db(self, key: str, value: str, cache_type: str,
                   created_at: float, expires_at: float):
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO cache (key, value, cache_type, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (key, value, cache_type, created_at, expires_at),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_from_db(self, key: str):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Stats (for debugging / status display)
    # ------------------------------------------------------------------

    @property
    def memory_size(self) -> int:
        return len(self._memory)

    @property
    def db_size(self) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()


# Singleton — shared by app.py and tools/base.py
_cache_singleton: Optional[CacheManager] = None


def get_shared_cache() -> CacheManager:
    """Get the global CacheManager singleton, creating it on first use."""
    global _cache_singleton
    if _cache_singleton is None:
        from poplar.config import get_cache_config
        cfg = get_cache_config()
        _cache_singleton = CacheManager(max_memory=cfg.get("max_memory_items", 100))
    return _cache_singleton
