# Token Calculation — Design

## Overview

Replace crude `len(text) // 4` estimate with a two-tier approach:
- **L1** — improved static estimate (CJK-aware) for threshold checks
- **L3** — exact `usage.total_tokens` from API responses for display

## Component: `core/token_tracker.py`

```python
class TokenTracker:
    def reset(self):
        self._api_total = 0          # cumulative from API usage reports

    def estimate(text: str) -> int:   # static (no state, no deps)
        ...

    def record_api(usage: dict):      # called after each API call
        self._api_total += usage["total_tokens"]

    def get_total(self) -> int:
        if self._api_total > 0:
            return self._api_total
        return TokenTracker.estimate(...)
```

## L1 Estimate

Replace `len(text) // 4` with:

```python
@staticmethod
def estimate(text: str) -> int:
    if not text:
        return 1
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
    other = len(text) - cjk
    return max(1, int(cjk * 0.6 + other * 0.3))
```

## L3 API Recording

In `_finalize_streaming`, replace `self._total_tokens += len(content)//3` with:

```python
# _fetch_response: after stream completes, usage is available
if response_chunks have usage data:
    token_tracker.record_api({"total_tokens": actual_usage})
```

Since `stream_sync` doesn't expose usage directly, use the accumulated `api_messages` token count from the last provider response. Fall back to estimate if unavailable.

For now: use `len(content) // 3` as fallback, and prioritize actual API `usage.total_tokens` when the streaming library supports it.

## Files Changed

| File | Action |
|------|--------|
| `core/token_tracker.py` | **NEW** — TokenTracker class |
| `core/context.py` | Modify — use `TokenTracker.estimate()` instead of local `estimate_tokens` |
| `tui/app.py` | Modify — `TokenTracker` instance, `record_api()` in `_finalize_streaming`, replace `_total_tokens` logic |

## Backward Compatibility

- Existing `estimate_tokens()` and `messages_token_count()` in `context.py` remain as wrappers
- No config changes needed
- Fallback to old behavior if API usage is not available
