# Multi-Provider Support — Design

## Goal
Allow Poplar to use different AI providers (DeepSeek, OpenAI, Anthropic, Ollama) interchangeably, switching at runtime without restart.

## Architecture

### Provider Registry (Factory)
```
providers/
├── __init__.py    # Registry + create_provider() factory
├── base.py        # Provider Protocol (unchanged)
├── deepseek.py    # DeepSeekProvider (existing, minor tweaks)
├── openai.py      # OpenAIProvider (new)
├── anthropic.py   # AnthropicProvider (new)
└── ollama.py      # OllamaProvider (new)
```

### Provider Protocol (existing, unchanged)
```python
class Provider(Protocol):
    def chat(self, messages: list[Message], **kwargs) -> ChatResponse: ...
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]: ...
    def get_models(self) -> list[ModelInfo]: ...
    def stream_sync(self, messages, **kwargs) -> Iterator[dict]: ...  # already on DeepSeek
```

Each new provider implements the same Protocol. The `stream_sync` method (used by the app's tool loop) must be implemented by all providers for consistent tool-calling support.

### Provider Registration

```python
# providers/__init__.py
PROVIDERS = {
    "deepseek":  {"module": ".deepseek",  "class": "DeepSeekProvider",  "env_key": "DEEPSEEK_API_KEY"},
    "openai":    {"module": ".openai",    "class": "OpenAIProvider",    "env_key": "OPENAI_API_KEY"},
    "anthropic": {"module": ".anthropic", "class": "AnthropicProvider", "env_key": "ANTHROPIC_API_KEY"},
    "ollama":    {"module": ".ollama",    "class": "OllamaProvider",    "env_key": None},
}

def create_provider(name: str, api_key: str = None, model: str = None, base_url: str = None) -> Provider: ...
```

### Provider Implementations

| Provider | SDK | Tool Support | Notes |
|----------|-----|--------------|-------|
| DeepSeek | `openai` SDK (compat) | ✅ via `stream_sync` | Existing, unchanged |
| OpenAI | `openai` SDK | ✅ via `stream_sync` | Same code pattern as DeepSeek |
| Anthropic | `anthropic` SDK | ⚠️ Functions (beta) | Different API; no `stream_sync` yet |
| Ollama | `requests` or `ollama` SDK | ✅ via chat API | Local, no API key needed |

**Decision:** Implement OpenAI first (same SDK as DeepSeek, trivial), then Ollama (useful for local testing, no API key), then Anthropic (different SDK, more work).

## Configuration

```yaml
# ~/.poplar/config.yaml
provider: deepseek  # default provider
providers:
  deepseek:
    model: deepseek-chat
  openai:
    model: gpt-4o
  anthropic:
    model: claude-3-5-sonnet-20241022
  ollama:
    base_url: http://localhost:11434
    model: llama3
```

API keys are read from environment variables (`DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Ollama needs no key.

## Runtime Provider Switching

- `/provider` — shows current provider
- `/provider list` — lists available providers + current
- `/provider set <name>` — switches provider, persists to config

When switching:
1. Save current session (already persisted)
2. Create new provider instance
3. Update StatusFooter with new model name
4. Next message uses new provider

## Files Changed

| File | Action |
|------|--------|
| `src/poplar/providers/__init__.py` | **NEW** — registry, factory |
| `src/poplar/providers/openai.py` | **NEW** — OpenAI provider |
| `src/poplar/providers/anthropic.py` | **NEW** — Anthropic provider |
| `src/poplar/providers/ollama.py` | **NEW** — Ollama provider |
| `src/poplar/providers/deepseek.py` | Modify — use registry patterns |
| `src/poplar/providers/base.py` | Maybe add `stream_sync` to Protocol |
| `src/poplar/i18n.py` | Add provider config defaults |
| `src/poplar/tui/app.py` | Use factory, add `/provider` command, StatusFooter shows provider name |
| `tests/test_providers.py` | **NEW** — tests for each provider |

## Implementation Order

1. Provider registry (`__init__.py`) + config defaults
2. OpenAI provider (reuse SDK pattern)
3. Update `app.py` to use factory + `/provider` command
4. Ollama provider (local, no API key)
5. Anthropic provider (different SDK)
6. Tests
