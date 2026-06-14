# Poplar — Cache & Context Management Design

## Overview

Improve Poplar's handling of long conversations and reduce redundant operations through two systems: **smart context summarization** (LLM-based compression) and **hybrid caching** (memory LRU + SQLite persistence).

---

## 1. Context Window Management — Smart Summarization

### Problem

Long conversations accumulate messages that consume token context. The current implementation sends all user/assistant messages without limit. DeepSeek models have 64K–128K context windows, but:
- Token cost increases linearly with conversation length
- Model quality degrades when context is near-full
- No mechanism to recover from context overflow

### Approach: LLM-based summarization

When the conversation approaches the token limit, earlier messages are compressed into a summary by the model itself, replacing the raw messages with a concise system message.

### Trigger

| Trigger | When |
|---------|------|
| **Auto** | Token count reaches **70%** of configured limit |
| **Manual** | User sends `/compress` command |

### Algorithm

```
1. Estimate current token count from API usage tracking
2. If above threshold → flag for compression
3. Keep the most recent N exchanges intact (default: 3)
4. Collect all messages before the kept window
5. Send to LLM with summarization prompt
6. Replace summarized messages with a single SYSTEM message:
   "[Summary of earlier conversation: ...]"
7. Update token tracking
```

### Summarization Prompt

```
Please summarize the following conversation concisely.
Keep all important facts, decisions, code changes, and user preferences.
Aim for 200-400 tokens. The summary will be used as context for the continuing conversation.

Conversation:
{earlier_messages}
```

### Storage

Summaries are stored as normal `Message(role=SYSTEM, content="[Summary: ...]")` in the session's message list. This means they persist across restarts via the existing `SessionStore`.

### Configuration

```yaml
# ~/.poplar/config.yaml
context:
  max_tokens: 32768          # Context window limit
  auto_compress_at: 0.7      # 70% of max_tokens triggers compression
  keep_recent_exchanges: 3   # Last N exchanges preserved intact
```

### Manual Command

- `/compress` — User-typed command in the composer triggers compression immediately.
- Detected in `on_composer_submit()` before sending to API.

### Key Decisions

- **Summarization uses the same provider** (DeepSeek) — no extra dependency.
- **Synchronous summarization** — runs as a worker thread; spinner shown during compression.
- **Summary replaces original messages** — no undo; summary is cumulative over multiple compressions.

---

## 2. Hybrid Cache System

### Problem

Repeat operations read the same files, list the same directories, and hit the same API endpoints. Current implementation executes every `read_file` or `list_directory` from disk.

### Approach: Two-tier Cache

```
┌──────────────┐     hit     ┌──────────────────┐
│  Memory LRU  │ ──────────→ │  Return cached    │
│  (OrderedDict)│             │  value            │
│  max=100      │             └──────────────────┘
└──────┬───────┘
       │ miss
       ▼
┌──────────────┐     hit     ┌──────────────────┐
│  SQLite Cache │ ──────────→ │  Promote to LRU   │
│  (poplar.db)  │             │  Return value     │
└──────┬───────┘
       │ miss
       ▼
┌──────────────┐
│  Execute &   │
│  Store in    │
│  LRU + SQLite│
└──────────────┘
```

### Cache Types and TTLs

| Type | Key | Value | TTL | Eviction |
|------|-----|-------|-----|----------|
| `tool_read_file` | `read_file:{resolved_path}` | File content (≤8K) | 5 min | LRU + TTL |
| `tool_list_directory` | `list_dir:{resolved_path}` | Directory listing text | 30 sec | LRU + TTL |
| `api_response` | `api:{sha256(json.dumps(messages, sort_keys=True))}` | Full response content | 1 hour | LRU + TTL |

> **Note:** API cache key includes the full messages array (including system prompt and tool results), serialized deterministically with sorted keys. Low hit rate for conversational messages, but useful for repeated tool calls with identical arguments.

### Invalidation

- `write_file` → invalidates `read_file` cache for the same path.
- `delete_session` → no cache invalidation needed (cache is per-process).

### Implementation

**New file: `src/poplar/persistence/cache.py`**

```python
class CacheManager:
    """Two-tier cache: memory LRU + SQLite persistence."""

    def __init__(self, db_path: str, max_memory: int = 100):
        self.max_memory = max_memory
        self._memory: OrderedDict[str, CacheEntry] = OrderedDict()
        self.db_path = db_path
        self._init_db()

    def get(self, key: str) -> Optional[str]:
        """Check memory first, then SQLite."""
        ...

    def set(self, key: str, value: str, ttl_seconds: int):
        """Store in both memory and SQLite."""
        ...
```

**Cache table schema:**

```sql
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    cache_type TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
```

**Memory tier:**
- `OrderedDict` with max 100 entries
- On access: move to end (LRU ordering)
- On insert beyond max: evict oldest (first) entry
- On eviction from memory: still in SQLite

**SQLite tier:**
- All cache entries persisted
- Cleanup on access: `DELETE FROM cache WHERE expires_at < ?`
- Used as fallback when memory misses

### Integration Points

| Cache Type | Where | How |
|------------|-------|-----|
| `read_file` | `tools/builtin.py` → `read_file()` | Check cache before read; store after read |
| `list_directory` | `tools/builtin.py` → `list_directory()` | Check cache before listing; store after |
| `api_response` | `tui/app.py` → `_fetch_response()` | Hash api_messages; check cache before API call; store after |

### Configuration

```yaml
# ~/.poplar/config.yaml
cache:
  enabled: true
  max_memory_items: 100
  tool_read_file_ttl: 300       # 5 min
  tool_list_dir_ttl: 30         # 30 sec
  api_response_ttl: 3600        # 1 hour
```

---

## 3. File Changes Summary

| File | Action |
|------|--------|
| `src/poplar/core/context.py` | **NEW** — `ContextManager` class |
| `src/poplar/persistence/cache.py` | **NEW** — `CacheManager` class |
| `src/poplar/tui/app.py` | Modify — add `/compress` handler, integrate cache in API calls |
| `src/poplar/tools/builtin.py` | Modify — add cache check/store in read_file, list_directory |
| `src/poplar/providers/deepseek.py` | Modify — expose token count from usage |
| `src/poplar/i18n.py` | Modify — add config defaults |
| `tests/test_context.py` | **NEW** — context manager tests |
| `tests/test_cache.py` | **NEW** — cache manager tests |

---

## 4. Key Decisions

1. **Summarization over truncation**: Preserves more information than simple message deletion.
2. **Same-model summarization**: No extra dependency; DeepSeek is cheap enough.
3. **Hybrid over pure memory**: Session restart retains cache (useful for tools like read_file).
4. **Separate context config**: Model-independent; user can set lower limit than model max.
5. **No tokenizer dependency**: Rough estimation (chars/4) for trigger; API `usage` for accuracy.

---

## 5. Backward Compatibility

- Existing `~/.poplar/config.yaml` files only have `language` and `model`. The new `context` and `cache` sections must be **optional** with sensible defaults.
- `i18n.py`'s `load_config()` must handle missing sections gracefully (use `dict.get()` with defaults).
- Cache table creation uses `CREATE TABLE IF NOT EXISTS` — safe to add alongside existing tables.

## 6. Open Questions

1. Summarization during an active API call — queue or block?
2. Cache key for API responses includes tool calls? (Tool call payloads vary a lot.)
