# Poplar — AI Agent TUI

Terminal-based AI chat application built with Python and Textual framework, integrating multiple AI providers (DeepSeek, OpenAI, Anthropic, Ollama) with tool execution, multi-session management, caching, context compression, and i18n support.

## Project

- **Stack:** Python >=3.10, Textual (TUI), OpenAI SDK (DeepSeek-compatible API), PyYAML, sqlite3 (stdlib)
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
├── i18n.py                 # Translations (en/zh), YAML config mgmt, t() helper
├── core/
│   └── session.py          # Data models: Role(Enum), Message(dataclass), Session(dataclass)
├── persistence/
│   └── store.py            # SessionStore: SQLite CRUD for sessions + messages + tool_calls
├── providers/
│   ├── __init__.py         # Provider registry + create_provider() factory
│   ├── base.py             # Provider Protocol (structural typing), ChatResponse, ModelInfo
│   ├── deepseek.py         # DeepSeekProvider: chat(), stream(), stream_sync(), get_models()
│   ├── openai.py           # OpenAIProvider (same pattern)
│   ├── anthropic.py        # AnthropicProvider (native tool_use)
│   └── ollama.py           # OllamaProvider (local, httpx-based)
├── tools/
│   ├── base.py             # ToolResult dataclass, TOOL_DEFINITIONS (OpenAI tool schema), execute_tool()
│   └── builtin.py          # Implementations: read_file, write_file, list_directory, run_command
└── tui/
    ├── app.py              # PoplarApp: main Textual App, StatusFooter, spinner, worker, tool loop
    ├── chat_view.py        # ChatView (ScrollableContainer) + ChatMessages (Static), welcome screen
    ├── composer.py         # Composer (Widget) wrapping TextArea, multi-line input
    └── session_picker.py   # SessionPicker: ModalScreen for switching/creating/deleting/renaming sessions
```

### Key patterns

- **Provider Protocol:** Uses Python structural typing (`Protocol`), not inheritance. `DeepSeekProvider` matches by having the right method signatures.
- **Reactive UI:** `ChatView.messages` is a Textual reactive attribute — `watch_messages()` auto-re-renders on change.
- **Async streaming:** `_fetch_response` is an `async def` method run via `self.run_worker()`. Chunks update the UI via `call_from_thread()`.
- **Tool loop:** Multi-turn: model requests tool → execute → append result → call model again → repeat until a content response.
- **i18n:** `t("key")` returns translated string from dicts in `i18n.py`. Language set via config or `POPLAR_LANGUAGE` env var.
- **Session persistence:** `SessionStore` (sqlite3) auto-creates DB on first run. Messages persist on each add.
- **Crash handling:** Unhandled exceptions go to `~/.poplar/logs/crash.log` via `sys.excepthook`.

## Conventions

- **Formatting:** Black with line-length=88; target Python 3.10.
- **Imports:** stdlib → third-party → local (blank-line separated groups).
- **Logging:** Use `logger = logging.getLogger(__name__)` in each module; log to `~/.poplar/logs/app.log`.
- **Messages:** Use `Role` enum (SYSTEM/USER/ASSISTANT/TOOL). `Message.to_dict()` for API serialization.
- **Testing:** pytest; tests live in `tests/` matching source module names. Use `conftest` patterns where needed.
- **UI text:** Always use `t("key")` for user-facing strings, never hardcode Chinese/English.
- **Git:** Conventional commits (`feat:`, `fix:`, `docs:`, etc.).
- **Do NOT:** hardcode API keys, commit `.venv/` or `__pycache__/`, or bypass the `SessionStore` for message persistence.
- **Config changes:** Read/write via `load_config()` / `save_config()` in `i18n.py`; new config keys get a default.

## Notes

(Add project-specific notes here as they arise.)
