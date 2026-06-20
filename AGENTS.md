# Poplar — AI Agent TUI

Terminal-based AI chat application built with Python and Textual framework, integrating multiple AI providers (DeepSeek, OpenAI, Anthropic, Ollama) with tool execution, multi-session management, caching, context compression, and i18n support.

## Project

- **Stack:** Python >=3.10, Textual (TUI), openai SDK + anthropic SDK, PyYAML, httpx, sqlite3 (stdlib)
- **Entry point:** `src/poplar/main.py` → `poplar.main:main` (installed as `poplar` CLI)
- **Config dir:** `~/.poplar/config.yaml` (language, model); DB at `~/.poplar/poplar.db`
- **Remote:** `github.com/mufanlee/poplar` (public)

## Commands

| Command | Purpose |
|---------|---------|
| `pip install -e .` | Install package in editable mode |
| `pip install -e ".[dev]"` | Install with dev deps (pytest, black, mypy) |
| `poplar` | Run the application |
| `python -m poplar.main` | Alternative run command |
| `pytest tests/ -v` | Run all tests |
| `pytest tests/test_store.py -v` | Run specific test file |
| `black src/ tests/` | Format code (88 char line length) |
| `mypy src/` | Type check |

## Architecture

```
src/poplar/
├── main.py                 # CLI entry point, crash handler setup
├── config.py               # Config load/save, defaults, provider/cache/context config
├── i18n.py                 # Translations (en/zh), t() helper, language detection
├── core/
│   ├── session.py          # Data models: Role(Enum), Message(dataclass), Session(dataclass)
│   ├── context.py          # ContextManager: token estimation, LLM summarization
│   └── stats.py            # StatsCollector: API latency, token usage, cache hit rate, /stats command
├── persistence/
│   ├── store.py            # SessionStore: SQLite CRUD for sessions + messages + tool_calls
│   └── cache.py            # CacheManager: two-tier (OrderedDict LRU + SQLite), tool/API caching
├── providers/
│   ├── __init__.py         # Provider registry + create_provider() factory
│   ├── base.py             # Provider Protocol (structural typing), ChatResponse, ModelInfo
│   ├── deepseek.py         # DeepSeekProvider: chat(), stream(), stream_sync(), get_models()
│   ├── openai.py           # OpenAIProvider (same pattern)
│   ├── anthropic.py        # AnthropicProvider (native tool_use via anthropic SDK)
│   └── ollama.py           # OllamaProvider (local, httpx-based, /api/tags for models)
├── tools/
│   ├── base.py             # ToolResult dataclass, TOOL_DEFINITIONS, execute_tool() with caching
│   └── builtin.py          # Implementations: read_file, write_file, list_directory, run_command
└── tui/
    ├── app.py              # PoplarApp: Textual App, StatusFooter, streaming, tool loop, commands
    ├── chat_view.py        # ChatView (ScrollableContainer) + MessageWidget (click-to-copy)
    ├── composer.py         # Composer: TextArea, Enter to send, Ctrl+Enter newline, /popup
    ├── session_picker.py   # SessionPicker: ModalScreen for switching/creating/deleting/renaming
    ├── cmd_prompt.py       # CommandSuggestion: slash-command popup with filtering
    └── help_screen.py      # HelpScreen: ModalScreen listing all /commands
```

### Key patterns

- **Provider Protocol:** Uses Python structural typing (`Protocol`), not inheritance.
- **Reactive UI:** `ChatView.messages` is a Textual reactive — `watch_messages()` triggers `_rebuild()`.
- **Worker thread streaming:** `_fetch_response` runs via `self.run_worker(..., thread=True)`. Chunks update the UI via `call_from_thread()`.
- **Tool loop:** Multi-turn: model requests tool → `execute_tool()` → append result → call model again → repeat until content response.
- **i18n:** `t("key")` returns translated string from `i18n.py`. Language set via config or `POPLAR_LANGUAGE` env var; cached after first read.
- **Config:** `config.py` manages `~/.poplar/config.yaml`. Defaults for cache, context, providers merged per-section.
- **Session persistence:** `SessionStore` (sqlite3) auto-creates DB on first run. Messages persist on each add.
- **Caching:** `CacheManager` singleton shared by tools and app. Two-tier: `OrderedDict` LRU + SQLite. Per-type TTL.
- **Crash handling:** Unhandled exceptions go to writable logs dir via `sys.excepthook`.
- **Commands:** All `/commands` handled in `app.py:on_composer_submit()`. `/help`, `/stats`, `/context`, `/compress`, `/export`, `/import`, `/provider`, `/clear`, `/session`, `/quit`.

## Conventions

- **Formatting:** Black with line-length=88; target Python 3.10.
- **Imports:** stdlib → third-party → local (blank-line separated groups).
- **Logging:** Use `logger = logging.getLogger(__name__)` in each module; log to `~/.poplar/logs/app.log`.
- **Messages:** Use `Role` enum (SYSTEM/USER/ASSISTANT/TOOL). `Message.to_dict()` for API serialization.
- **Testing:** pytest; tests live in `tests/` matching source module names. Use `conftest` patterns where needed.
- **UI text:** Always use `t("key")` for user-facing strings, never hardcode Chinese/English.
- **Git:** Conventional commits (`feat:`, `fix:`, `docs:`, etc.).
- **Do NOT:** hardcode API keys, commit `.venv/` `__pycache__/` `reasonix.toml` or `poplar-session-*.json`.
- **Config changes:** Read/write via `load_config()` / `save_config()` in `config.py`; new config keys get a default.
- **Log fallback:** When `~/.poplar/` is not writable (read-only filesystem), logs/DB fall back to `Path.cwd() / ".poplar/"`.
