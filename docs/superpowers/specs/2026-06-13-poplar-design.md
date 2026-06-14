# Poplar AI Agent TUI - Design Document

## Overview

Poplar is a Python-based AI Agent TUI application built with Textual framework. The project follows a three-phase evolution plan: MVP (learning), feature-complete, and production-ready.

**Core Value Proposition:** A learning-focused AI Agent TUI that grows from minimal viable product to production-grade application through iterative development.

## Architecture

### Layered Architecture

```
┌─────────────────────────────────────┐
│         TUI Layer (Textual)         │
│  ┌──────────┬──────────┬─────────┐  │
│  │ ChatView │ Sidebar  │ Footer  │  │
│  └──────────┴──────────┴─────────┘  │
├─────────────────────────────────────┤
│       Agent Core Layer              │
│  ┌──────────┬──────────┬─────────┐  │
│  │ Session  │ Tools    │ Sub-    │  │
│  │ Manager  │ Executor │ Agents  │  │
│  └──────────┴──────────┴─────────┘  │
├─────────────────────────────────────┤
│      Model Integration Layer        │
│  ┌───────────────────────────────┐  │
│  │   Provider Abstraction        │  │
│  │   (DeepSeek -> OpenAI compat) │  │
│  └───────────────────────────────┘  │
├─────────────────────────────────────┤
│       Persistence Layer             │
│  ┌──────────┬──────────┬─────────┐  │
│  │ History  │ Config   │ Cache   │  │
│  └──────────┴──────────┴─────────┘  │
└─────────────────────────────────────┘
```

## Core Components

### 1. TUI Layer (Textual)

#### ChatView
- Displays conversation history with message bubbles
- Supports markdown rendering for code blocks
- Auto-scrolls to latest message
- Shows thinking/reasoning content in collapsible sections

#### Composer
- Multi-line input using Textual TextArea widget
- Keyboard shortcuts: Enter (send), Ctrl+Enter (new line), Esc (cancel)
- Auto-titles sessions based on first message content

#### SessionPicker (Modal Screen)
- Modal dialog triggered by Ctrl+S
- Navigate sessions with ↑/↓, switch with Enter
- Create (N), delete (D), rename (R) sessions
- Displays message count per session

#### StatusFooter
- Displays current model name, token count, and message count
- Updated in real-time during conversation

### 2. Agent Core Layer

#### SessionManager
- Manages multiple conversation sessions
- Persists session metadata (title, created_at, message_count)
- Handles session creation, deletion, switching
- Exports/imports session data

#### Tool Execution
- Tools defined as OpenAI function-calling schema in `tools/base.py`
- Built-in tools (implemented in `tools/builtin.py`):
  - `read_file`: Read file contents (truncated at 8000 chars)
  - `write_file`: Write/create files with auto-creating parent dirs
  - `list_directory`: List directory contents with sizes
  - `run_command`: Execute shell commands
- Multi-turn automatic execution: model calls tool → execute → append result → loop until content response
- All tools auto-execute without approval prompt

#### SubAgentRouter (Phase 2+)
- Routes complex tasks to specialized sub-agents
- Pre-defined sub-agents:
  - Code reviewer
  - Documentation writer
  - Test generator
  - Bug fixer
- Each sub-agent has its own system prompt and tool set
- Results merged back into main conversation

### 3. Model Integration Layer

#### Provider Interface
```python
class Provider(Protocol):
    def chat(self, messages: list[Message], **kwargs) -> ChatResponse
    def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]
    def get_models(self) -> list[ModelInfo]
```

#### DeepSeekProvider
- Uses OpenAI-compatible API endpoint
- Base URL: `https://api.deepseek.com/v1`
- Supports chat completions and streaming
- Handles rate limiting and retry logic
- Token counting for cost tracking

#### MessageFormatter
- Converts internal Message format to provider-specific format
- Handles system prompts, user messages, assistant responses
- Manages context window limits
- Implements message compaction strategies

### 4. Persistence Layer

#### SessionStore (SQLite)
- Tables: `sessions` (id, title, created_at, updated_at), `messages` (session_id, role, content, tool_calls, created_at)
- DB path: `~/.poplar/poplar.db`
- Auto-creates database and tables on first use
- Methods: create_session, get_session, list_sessions, save_message, delete_session, update_title

#### ConfigManager
- YAML configuration file at `~/.poplar/config.yaml`
- Settings: language (en/zh), model (deepseek-chat/deepseek-coder)
- Auto-created on first run with defaults
- Environment variable override: `POPLAR_LANGUAGE`
- API key via `DEEPSEEK_API_KEY` environment variable only

#### Cache (LRU)
- Token count caching
- Model response caching (optional, TTL-based)
- File content caching for repeated reads
- Directory listing cache

## Data Flow

### User Message Flow
```
User types in Composer
    → ChatView displays message
    → SessionManager saves to database
    → AgentCore sends to Provider
    → Provider streams response
    → ChatView renders incrementally
    → SessionManager saves response
```

### Tool Execution Flow
```
Model requests tool call
    → ToolExecutor validates request
    → Approval check (if dangerous operation)
    → Execute tool
    → Format result
    → Send result back to model
    → Model generates follow-up response
```

### Sub-Agent Flow (Phase 2+)
```
Main agent delegates task
    → SubAgentRouter selects appropriate sub-agent
    → Create isolated context
    → Sub-agent executes with specialized tools
    → Results returned to main conversation
    → Main agent synthesizes final response
```

## Error Handling

### Categories
- **Network errors**: Retry with exponential backoff
- **API errors**: Display user-friendly messages, suggest alternatives
- **Tool errors**: Capture stderr, show in chat, allow retry
- **Configuration errors**: Guide user through setup wizard

### Recovery Strategies
- Auto-save draft messages before sending
- Session recovery after crash
- Graceful degradation when API unavailable
- Offline mode for viewing history

## Testing Strategy

### Unit Tests
- Provider interface implementations
- Message formatting logic
- Configuration parsing
- Database operations

### Integration Tests
- End-to-end conversation flow
- Tool execution pipeline
- Session management operations

### UI Tests (Textual)
- Component rendering
- Keyboard interaction
- Layout responsiveness

## File Structure

```
poplar/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── .env.example
├── .gitignore
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-06-13-poplar-design.md
│       └── plans/
│           └── 2026-06-13-poplar-phase1-mvp.md
├── src/
│   └── poplar/
│       ├── __init__.py
│       ├── main.py                      # Entry point + crash handler
│       ├── i18n.py                      # Internationalization + config
│       ├── core/
│       │   ├── __init__.py
│       │   └── session.py               # Data models: Role, Message, Session
│       ├── persistence/
│       │   ├── __init__.py
│       │   └── store.py                 # SQLite SessionStore
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py                  # Provider Protocol
│       │   └── deepseek.py              # DeepSeek impl with stream_sync()
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py                  # Tool schemas + execute_tool()
│       │   └── builtin.py              # Tool implementations
│       └── tui/
│           ├── __init__.py
│           ├── app.py                   # PoplarApp: main loop, streaming, tools
│           ├── chat_view.py             # Message display + welcome screen
│           ├── composer.py              # Multi-line TextArea input
│           └── session_picker.py        # Modal dialog for session management
├── tests/
│   ├── __init__.py
│   ├── test_session.py
│   ├── test_deepseek_provider.py
│   ├── test_i18n.py
│   ├── test_store.py
│   └── test_tools.py
└── examples/
    └── config.example.yaml
```

## Phase Definitions

### Phase 1: MVP (Learning)
**Goal:** Working chat interface with DeepSeek integration

**Features:**
- Basic TUI with chat view and composer
- DeepSeek API integration (non-streaming)
- Simple session management (single session)
- In-memory history (no persistence)
- No tools, no sub-agents

**Success Criteria:**
- Can send message and receive response
- Conversation persists during session
- Clean shutdown without data loss

### Phase 2: Feature-Complete ✅
**Completion Date:** 2026-06-14

**Goal:** Full-featured local AI Agent

**Features:**
- All TUI components (ChatView, Composer with TextArea, StatusFooter, Welcome screen, SessionPicker modal)
- Tool execution (read_file, write_file, list_directory, run_command) with multi-turn loop
- SQLite persistence for session history and messages
- Configuration management (language, model via YAML + env vars)
- Streaming responses (token-by-token via async worker)
- Multiple session support (create, switch, delete, rename via Ctrl+S)
- API retry with exponential backoff
- Message queuing (type while waiting)
- Crash logging to `~/.poplar/logs/crash.log`
- Context engineering (system prompt, thinking message filtering)

**Success Criteria:**
- ✅ Can complete coding tasks with tools
- ✅ Sessions survive application restart
- ✅ Streaming responses display in real-time
- ✅ Multiple sessions can be managed

### Phase 3: Production-Ready
**Goal:** Robust, extensible application

**Features:**
- Plugin system for custom tools
- Multi-provider support (OpenAI, Anthropic, Ollama)
- Advanced caching and optimization
- Comprehensive error handling
- Export/import functionality
- Theme customization
- Keybinding configuration
- Performance monitoring
- Documentation and examples

**Success Criteria:**
- Stable under extended use
- Extensible via plugins
- Good performance with large contexts
- Clear documentation for users and developers

## Phase 1 Implementation Summary

**Completed:** 2026-06-14

### Implemented Features

#### Core Functionality
- ✅ Basic TUI with Textual framework
- ✅ DeepSeek API integration (non-streaming, synchronous with background threading)
- ✅ Simple session management (single session, in-memory)
- ✅ Message history with role-based display (User/Assistant/System)

#### UI Components
- ✅ **Header**: Application title "🌳 Poplar" with clock
- ✅ **ChatView**: Scrollable message display with rounded borders and themed scrollbars
- ✅ **Composer**: User input field with i18n placeholder
- ✅ **StatusFooter**: Model name, token count, message count display
- ✅ **Footer**: Keyboard shortcuts display
- ✅ **Welcome Screen**: Centered welcome message with quick start guide

#### UI Enhancements (Beyond Original Plan)
- ✅ Message bubbles with different styles (blue for user, green for assistant)
- ✅ Markdown rendering for assistant responses
- ✅ Spinner animation with Braille characters during API calls
- ✅ Elapsed time display in thinking indicator
- ✅ ESC key to cancel ongoing API requests
- ✅ Error handling with user-friendly messages

#### Internationalization (Beyond Original Plan)
- ✅ Bilingual support: English (default) and Chinese
- ✅ Configuration via `~/.poplar/config.yaml`
- ✅ Environment variable override: `POPLAR_LANGUAGE`
- ✅ Automatic config file creation on first run

#### Configuration Management (Beyond Original Plan)
- ✅ YAML-based configuration file
- ✅ Model selection (deepseek-chat, deepseek-coder)
- ✅ Language preference persistence

#### Developer Features
- ✅ Logging to `poplar.log`
- ✅ Proxy environment variable clearing (IPv6 compatibility)
- ✅ Token and message counting

### Actual File Structure (Phase 1)

```
poplar/
├── pyproject.toml
├── README.md
├── .env.example
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-06-13-poplar-design.md
│       └── plans/
│           └── 2026-06-13-poplar-phase1-mvp.md
├── src/
│   └── poplar/
│       ├── __init__.py
│       ├── main.py
│       ├── i18n.py                      # New: Internationalization
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── app.py                   # Main application with StatusFooter
│       │   ├── chat_view.py             # Chat display with welcome screen
│       │   └── composer.py              # User input
│       ├── core/
│       │   ├── __init__.py
│       │   └── session.py               # In-memory session management
│       └── providers/
│           ├── __init__.py
│           ├── base.py                  # Provider protocol interface
│           └── deepseek.py              # DeepSeek implementation
├── tests/
│   ├── __init__.py
│   ├── test_session.py
│   └── test_deepseek_provider.py
└── examples/
    └── config.example.yaml
```

### Configuration File Format

```yaml
# ~/.poplar/config.yaml
language: en              # en or zh
model: deepseek-chat      # deepseek-chat or deepseek-coder
```

### Keyboard Shortcuts

- `Enter` - Send message
- `Ctrl+Enter` - New line
- `Ctrl+S` - Open session picker
- `Ctrl+C` - Copy last assistant response
- `Ctrl+Q` - Quit application
- `ESC` - Cancel ongoing API request

### Configuration File Format

```yaml
# ~/.poplar/config.yaml
language: en              # en or zh
model: deepseek-chat      # deepseek-chat or deepseek-coder
```

**Note:** API key is set via environment variable `DEEPSEEK_API_KEY` only.

### Known Limitations (Phase 1)

- No persistence (sessions lost on restart) — *resolved in Phase 2*
- Single session only (no session switching) — *resolved in Phase 2*
- No streaming responses (synchronous API calls) — *resolved in Phase 2*
- No tool execution — *resolved in Phase 2*
- No sub-agent routing *(deferred)*
- No sidebar UI — *replaced by modal SessionPicker in Phase 2*

## Phase 2 Implementation Summary

**Completed:** 2026-06-14

### Implemented Features

#### New Modules
- ✅ **`persistence/store.py`**: `SessionStore` — SQLite CRUD for sessions, messages, and tool_calls. Auto-creates `~/.poplar/poplar.db` on first run.
- ✅ **`tools/base.py`**: Tool definitions (OpenAI function-calling schema) and `execute_tool()` dispatcher.
- ✅ **`tools/builtin.py`**: Four built-in tools — `read_file`, `write_file`, `list_directory`, `run_command`.

#### Core Enhancements (app.py)
- ✅ **Streaming responses**: `_fetch_response` changed from sync thread to `async def` worker. Token-by-token real-time display via `_update_streaming()` + `_finalize_streaming()`.
- ✅ **Multi-turn tool loop**: After receiving a `tool_calls` response, the app executes each tool, appends results as `role=tool` messages, re-calls the model, and loops until a content response is received.
- ✅ **Message queuing**: New messages typed while the API is still responding are queued in `_pending_queue` and processed automatically when the current response completes.
- ✅ **API retry**: `_call_with_retry()` — 3 attempts with exponential backoff (1s, 2s, 4s). Only retries on transient errors (timeout, rate limit, 5xx).
- ✅ **Crash logging**: Unhandled exceptions captured by `sys.excepthook` → `~/.poplar/logs/crash.log`.
- ✅ **Copy response**: `action_copy_response()` binds Ctrl+C to copy last assistant message via `pyperclip`.
- ✅ **System prompt**: Hardcoded `SYSTEM_PROMPT` guides model behavior; `_get_api_messages()` filters out thinking/spinner messages before API calls.

#### Multi-Session Management
- ✅ **`tui/session_picker.py`**: `SessionPicker(ModalScreen)` — triggered by Ctrl+S. Navigate with ↑/↓, create (N), delete (D), rename (R), switch (Enter).
- ✅ **Auto-title**: First user message auto-names the session (truncated to 30 chars).
- ✅ **Persistence**: Sessions and messages survive application restart via SQLite.

#### UI Changes
- ✅ **Composer**: Upgraded from `Input` to `TextArea` — multi-line input with Enter to send, Ctrl+Enter for newline.
- ✅ **Logging**: Moved from `poplar.log` (project dir) to `~/.poplar/logs/app.log`.
- ✅ **SessionPicker modal** replaces the originally planned sidebar.

### Bug Fixes
- `Message.to_dict()` — added missing `content` field to prevent API 400 errors.
- Tool call message format — fixed to match OpenAI protocol (`tool_calls` array, `tool_call_id`/`name` for tool role).
- Streaming multi-turn — fixed response overwrite / spinner stuck after tool completion.
- `_message_count` — properly initialized on session load.
- `push_screen` — handled missing `dismiss` callback values.
- ESC during streaming — properly cancels async worker.
- Rename mode — properly exits on Escape.

### Actual File Structure (Phase 2)

```
poplar/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── .env.example
├── .gitignore
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-06-13-poplar-design.md
│       └── plans/
├── src/
│   └── poplar/
│       ├── __init__.py
│       ├── main.py                      # Entry point + crash handler
│       ├── i18n.py                      # i18n + config
│       ├── core/
│       │   ├── __init__.py
│       │   └── session.py               # Role, Message, Session
│       ├── persistence/
│       │   ├── __init__.py
│       │   └── store.py                 # NEW: SessionStore (SQLite)
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py                  # Provider Protocol
│       │   └── deepseek.py              # stream_sync() added
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py                  # NEW: Tool schemas
│       │   └── builtin.py              # NEW: Tool implementations
│       └── tui/
│           ├── __init__.py
│           ├── app.py                   # Streaming + tool loop + queuing
│           ├── chat_view.py
│           ├── composer.py              # TextArea multi-line
│           └── session_picker.py        # NEW: Modal session manager
├── tests/
│   ├── __init__.py
│   ├── test_session.py
│   ├── test_deepseek_provider.py
│   ├── test_i18n.py                    # NEW
│   ├── test_store.py                   # NEW
│   └── test_tools.py                  # NEW
└── examples/
    └── config.example.yaml
```

### Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| `test_session.py` | Message/Session CRUD, serialization | ~90% |
| `test_deepseek_provider.py` | Provider init, chat/stream | ~60% |
| `test_i18n.py` | Config load/save, translations | ~70% |
| `test_store.py` | SessionStore CRUD, persistence | ~95% |
| `test_tools.py` | Tool execution, edge cases | ~85% |

**Total: 35 tests, ~29% overall code coverage (Phase 1: 15%)**

### Deferred to Phase 3
- Sub-agent routing
- Plugin system for custom tools
- Multi-provider support (OpenAI, Anthropic, Ollama)
- Advanced caching and optimization
- Export/import functionality
- Theme customization
- Keybinding configuration

## Dependencies

### Core
- `textual>=0.50.0` - TUI framework
- `openai>=1.0.0` - API client (compatible with DeepSeek)
- `pyyaml>=6.0` - Configuration parsing

### Dev
- `pytest>=7.0.0` - Testing framework
- `black>=23.0.0` - Code formatting
- `mypy>=1.0.0` - Type checking

## Configuration Example

```yaml
# ~/.poplar/config.yaml
language: en              # en or zh
model: deepseek-chat      # deepseek-chat or deepseek-coder
```

**Note:** API key is set via environment variable `DEEPSEEK_API_KEY`.

## Key Decisions

1. **Python over Rust**: Lower learning curve, faster iteration for learning project
2. **Textual over curses**: Modern framework with good documentation and component model
3. **DeepSeek first**: Cost-effective, good Chinese support, OpenAI-compatible API
4. **SQLite over JSON**: Better query capabilities, atomic writes, concurrent access (stdlib, no extra dep)
5. **ModalScreen over sidebar**: SessionPicker as modal dialog (Ctrl+S) instead of persistent sidebar — simpler UI, less layout complexity
6. **Three-phase approach**: Manageable scope, clear progression path, early wins

## Open Questions

1. Should we support WebSocket connections for real-time collaboration? *(Phase 3)*
2. What's the strategy for handling very long conversations? *(Compaction vs truncation — deferred)*
3. How to implement secure credential storage? *(Keyring integration? — deferred)*
4. Tool approval workflow? *(Currently auto-executes all tools — Phase 3 enhancement)*

## Success Metrics

- **MVP**: First successful API call within 2 hours of setup
- **Feature-Complete**: Can complete simple coding task end-to-end
- **Production**: Daily active users, positive feedback on usability
