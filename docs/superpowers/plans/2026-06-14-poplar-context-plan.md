# Context Management — Implementation Plan

Based on `docs/superpowers/specs/2026-06-14-poplar-cache-context-design.md`

## Steps

### Step 1: Create `src/poplar/core/context.py`
- `ContextManager` class
- Token estimation (`len(text) / 4`)
- `should_compress(messages, max_tokens, threshold)` — check if compression needed
- `get_summarizable_messages(messages, keep_recent)` — split into old + recent
- `summarize(summarizer_fn, messages)` — calls LLM to compress
- `apply_compression(session, summary, keep_recent)` — replace old messages with summary message

### Step 2: Add context config to `i18n.py`
- `max_tokens`, `auto_compress_at`, `keep_recent_exchanges` in config defaults
- `get_context_config()` function

### Step 3: Integrate into `app.py`
- Auto-compress: after API response, check token count, trigger if above threshold
- Manual `/compress` command: detect in `on_composer_submit()`, trigger compression
- Track accumulated token count from API usage
- Show spinner during compression

### Step 4: Test
- Test token estimation, message splitting, compression logic
