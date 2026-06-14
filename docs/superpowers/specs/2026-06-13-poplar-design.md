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
- Multi-line input field for user messages
- Keyboard shortcuts: Enter (send), Ctrl+Enter (new line), Esc (cancel)
- Shows character/token count
- Supports @mentions for tool invocation

#### Sidebar
- Session list with search/filter
- Model selector dropdown
- Token usage statistics
- Settings access

#### StatusBar
- Current mode indicator (chat, tool-executing, thinking)
- Keyboard shortcut hints
- Connection status
- Cost tracking

### 2. Agent Core Layer

#### SessionManager
- Manages multiple conversation sessions
- Persists session metadata (title, created_at, message_count)
- Handles session creation, deletion, switching
- Exports/imports session data

#### ToolExecutor
- Executes tools based on model requests
- Built-in tools:
  - `read_file`: Read file contents
  - `write_file`: Write/create files
  - `list_directory`: List directory contents
  - `run_command`: Execute shell commands (with approval)
  - `search_code`: Search codebase using grep/ripgrep
- Approval workflow for dangerous operations
- Tool result formatting for model consumption

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

#### HistoryStore (SQLite)
- Tables: sessions, messages, tool_calls
- Indexed queries for fast retrieval
- Automatic cleanup of old sessions
- Backup/export functionality

#### ConfigManager
- YAML configuration file at `~/.config/poplar/config.yaml`
- Settings: API keys, default model, theme, keybindings
- Environment variable overrides
- Per-project configuration support

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
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-06-13-poplar-design.md
│       └── plans/
├── src/
│   └── poplar/
│       ├── __init__.py
│       ├── main.py
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── chat_view.py
│       │   ├── composer.py
│       │   ├── sidebar.py
│       │   └── status_bar.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── session_manager.py
│       │   ├── tool_executor.py
│       │   └── subagent_router.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── deepseek.py
│       ├── persistence/
│       │   ├── __init__.py
│       │   ├── history_store.py
│       │   └── config_manager.py
│       └── tools/
│           ├── __init__.py
│           ├── file_ops.py
│           ├── shell.py
│           └── search.py
├── tests/
│   ├── __init__.py
│   ├── test_providers.py
│   ├── test_tools.py
│   └── test_session_manager.py
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

### Phase 2: Feature-Complete
**Goal:** Full-featured local AI Agent

**Features:**
- All TUI components (sidebar, status bar)
- Tool execution (file ops, shell commands)
- SQLite persistence for history
- Configuration management
- Streaming responses
- Multiple session support
- Basic sub-agent routing

**Success Criteria:**
- Can complete coding tasks with tools
- Sessions survive application restart
- Tool approval workflow functions
- Sub-agents handle specialized tasks

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
- `Ctrl+Q` - Quit application
- `ESC` - Cancel ongoing API request

### Known Limitations

- No persistence (sessions lost on restart)
- Single session only (no session switching)
- No streaming responses (synchronous API calls)
- No tool execution
- No sub-agent routing
- No sidebar UI

## Dependencies

### Core
- `textual>=0.50.0` - TUI framework
- `openai>=1.0.0` - API client (compatible with DeepSeek)
- `pyyaml>=6.0` - Configuration parsing
- `aiosqlite>=0.19.0` - Async SQLite support

### Optional (Phase 3)
- `rich>=13.0.0` - Enhanced terminal output
- `click>=8.0.0` - CLI interface
- `pytest>=7.0.0` - Testing framework
- `black>=23.0.0` - Code formatting
- `mypy>=1.0.0` - Type checking

## Configuration Example

```yaml
# ~/.config/poplar/config.yaml
providers:
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: "https://api.deepseek.com/v1"
    default_model: "deepseek-chat"

ui:
  theme: "dark"
  show_token_count: true
  max_sidebar_width: 30

session:
  auto_save: true
  max_history_sessions: 50
  compaction_threshold: 10000  # tokens

tools:
  require_approval:
    - run_command
    - write_file
  allowed_directories:
    - "~/workspace"
```

## Key Decisions

1. **Python over Rust**: Lower learning curve, faster iteration for learning project
2. **Textual over curses**: Modern framework with good documentation and component model
3. **DeepSeek first**: Cost-effective, good Chinese support, OpenAI-compatible API
4. **SQLite over JSON**: Better query capabilities, atomic writes, concurrent access
5. **Three-phase approach**: Manageable scope, clear progression path, early wins

## Open Questions

1. Should we support WebSocket connections for real-time collaboration? (Phase 3)
2. What's the strategy for handling very long conversations? (Compaction vs truncation)
3. How to implement secure credential storage? (Keyring integration?)
4. Should tools be synchronous or async? (Async preferred for non-blocking UI)

## Success Metrics

- **MVP**: First successful API call within 2 hours of setup
- **Feature-Complete**: Can complete simple coding task end-to-end
- **Production**: Daily active users, positive feedback on usability
