# Cache System — Implementation Plan

Based on `docs/superpowers/specs/2026-06-14-poplar-cache-context-design.md`

## Steps

### Step 1: Create `src/poplar/persistence/cache.py`
- `CacheManager` class with `OrderedDict` memory LRU (max 100) + SQLite backing
- `get(key)` / `set(key, value, ttl)` / `invalidate(pattern)` / `clear()`
- Cache table in `~/.poplar/poplar.db` (same DB as sessions)
- Auto-cleanup expired entries on access

### Step 2: Add cache config defaults to `i18n.py`
- Add `load_cache_config()` or extend `load_config()` with cache defaults
- Config keys under `cache:` section: `enabled`, `max_memory_items`, TTLs

### Step 3: Integrate cache into `tools/builtin.py`
- `read_file()` → check cache before read, store after read
- `list_directory()` → check cache before listing, store after
- `write_file()` → invalidate `read_file:{path}` after write

### Step 4: Integrate cache into `tui/app.py`
- In `_fetch_response()`: hash api_messages → check cache before API call → store after
- Only cache non-streaming responses (or cache the accumulated stream result)

### Step 5: Create `tests/test_cache.py`
- Test set/get, TTL expiry, LRU eviction, invalidation, persistence across sessions

### Step 6: Install, run tests, verify
