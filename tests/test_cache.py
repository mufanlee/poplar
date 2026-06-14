"""Tests for the cache system."""

import time
import pytest
from poplar.persistence.cache import CacheManager, make_key, hash_messages
from poplar.core.session import Message, Role


@pytest.fixture
def cache():
    """Fresh CacheManager with temp DB per test."""
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".db")
    c = CacheManager(db_path=tmp)
    yield c
    try:
        os.unlink(tmp)
    except OSError:
        pass


class TestCacheManager:
    def test_set_get(self, cache):
        cache.set("k", "v", 60)
        assert cache.get("k") == "v"

    def test_get_miss(self, cache):
        assert cache.get("nonexistent") is None

    def test_expiry(self, cache):
        cache.set("k", "v", ttl_seconds=0)  # Already expired
        assert cache.get("k") is None

    def test_invalidate_prefix(self, cache):
        cache.set("tool:read_file:/a", "a", 60)
        cache.set("tool:read_file:/b", "b", 60)
        cache.set("api:abc123", "response", 60)
        cache.invalidate("tool:read_file:")
        assert cache.get("tool:read_file:/a") is None
        assert cache.get("tool:read_file:/b") is None
        assert cache.get("api:abc123") == "response"

    def test_invalidate_no_match(self, cache):
        cache.set("a:1", "v", 60)
        cache.invalidate("b:")
        assert cache.get("a:1") == "v"

    def test_clear(self, cache):
        cache.set("a", "1", 60)
        cache.set("b", "2", 60)
        cache.clear()
        assert cache.get("a") is None
        assert cache.db_size == 0

    def test_lru_eviction(self, cache):
        cache.max_memory = 3
        cache.set("a", "1", 60)
        cache.set("b", "2", 60)
        cache.set("c", "3", 60)
        cache.set("d", "4", 60)  # Should evict "a" from memory
        # "a" is evicted from memory but still in SQLite
        assert "a" not in cache._memory, "a should be evicted from memory"
        assert cache.memory_size == 3
        assert cache.db_size == 4

    def test_lru_eviction_db_fallback(self, cache):
        """Evicted from memory can still be retrieved from SQLite."""
        cache.max_memory = 2
        cache.set("a", "1", 60)
        cache.set("b", "2", 60)
        cache.set("c", "3", 60)  # Evicts "a" from memory
        assert "a" not in cache._memory
        # But still accessible via SQLite
        assert cache.get("a") == "1"
        # Access promotes it back to memory
        assert "a" in cache._memory

    def test_get_or_compute_caches(self, cache):
        call_count = [0]
        def compute():
            call_count[0] += 1
            return "computed"
        
        val = cache.get_or_compute("test", 60, compute)
        assert val == "computed"
        assert call_count[0] == 1

        val2 = cache.get_or_compute("test", 60, compute)
        assert val2 == "computed"
        assert call_count[0] == 1  # Not called again

    def test_get_or_compute_on_miss(self, cache):
        """Test that a new key triggers compute even after cache was cleared."""
        cache.get_or_compute("key", 60, lambda: "first")
        cache.clear()
        val = cache.get_or_compute("key", 60, lambda: "second")
        assert val == "second"

    def test_memory_promotion_from_db(self, cache):
        """A value in SQLite but not memory should be promoted on get."""
        cache.set("k", "v", 60)
        cache._memory.clear()  # Remove from memory
        assert cache.memory_size == 0

        val = cache.get("k")
        assert val == "v"
        assert cache.memory_size == 1  # Promoted back to memory

    def test_memory_move_to_end_on_access(self, cache):
        """Accessing a key should move it to the end (most recently used)."""
        cache.max_memory = 2
        cache.set("a", "1", 60)
        cache.set("b", "2", 60)
        cache.get("a")  # Access a - makes it most recent
        cache.set("c", "3", 60)  # Should evict "b" from memory
        # "a" is most recently used so stays in memory
        assert "a" in cache._memory
        # "b" should be evicted from memory (least recently used)
        assert "b" not in cache._memory
        assert cache.memory_size == 2
        # But "b" can still be retrieved from SQLite
        assert cache.get("b") == "2"

    def test_stats(self, cache):
        assert cache.memory_size == 0
        assert cache.db_size == 0
        cache.set("k1", "v1", 60)
        cache.set("k2", "v2", 60)
        assert cache.memory_size == 2
        assert cache.db_size == 2


class TestHelpers:
    def test_make_key(self):
        assert make_key("tool", "read_file") == "tool:read_file"
        assert make_key("api", "abc123") == "api:abc123"

    def test_hash_messages(self):
        msgs = [
            Message(role=Role.SYSTEM, content="You are Poplar"),
            Message(role=Role.USER, content="hello"),
        ]
        h = hash_messages(msgs)
        assert len(h) == 16
        assert isinstance(h, str)

    def test_hash_messages_deterministic(self):
        msgs = [Message(role=Role.USER, content="hello")]
        h1 = hash_messages(msgs)
        h2 = hash_messages(msgs)
        assert h1 == h2

    def test_hash_messages_different_content(self):
        m1 = [Message(role=Role.USER, content="hello")]
        m2 = [Message(role=Role.USER, content="world")]
        assert hash_messages(m1) != hash_messages(m2)

    def test_hash_messages_system_filtered_out_not_needed(self):
        """hash_messages includes system messages in the hash."""
        msgs = [Message(role=Role.SYSTEM, content="prompt"), Message(role=Role.USER, content="hi")]
        h = hash_messages(msgs)
        assert len(h) == 16
