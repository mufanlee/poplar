# Poplar

AI Agent TUI application built with Python and Textual framework.

## Overview

Poplar (杨树) is a terminal-based AI chat application built with Python and Textual framework. It features a rich terminal user interface with support for multiple AI providers (DeepSeek, OpenAI, Anthropic, Ollama), tool execution, multi-session management, and internationalization.

## Features

### Core Features
- **Rich TUI Interface**: Built with Textual framework, featuring rounded borders, themed scrollbars, and message bubbles
- **Multi-Provider Support**: DeepSeek, OpenAI, Anthropic, and Ollama — switch at runtime with `/provider set <name>`
- **Streaming Responses**: Token-by-token real-time display of AI responses
- **Tool Execution**: Built-in tools for file read/write, directory listing, and shell commands — multi-turn automatic execution
- **Multi-Session Management**: Create, switch, delete, and rename sessions (Ctrl+S)
- **SQLite Persistence**: Conversations survive application restart
- **Context Compression**: Automatic LLM-based summarization of long conversations
- **Smart Caching**: Hybrid memory + SQLite cache for tools and API responses
- **Markdown Rendering**: Assistant responses support Markdown formatting
- **Multi-line Input**: TextArea with Ctrl+Enter for new lines
- **Message Queuing**: Continue typing while waiting — messages auto-send after response
- **Request Cancellation**: Press ESC to cancel ongoing API requests
- **API Retry**: Automatic retry with exponential backoff on failures
- **Copy Response**: Ctrl+C to copy the last assistant response
- **Session Export/Import**: Save and load conversations with `/export` and `/import`
- **Internationalization**: Support for English and Chinese languages
- **Configuration Management**: YAML-based configuration file with provider, model, and language settings

### UI Components
- **Header**: Displays application title "🌳 Poplar" and clock
- **ChatView**: Scrollable message display area with message bubbles
- **Composer**: Multi-line input using TextArea (Enter to send, Ctrl+Enter for new line)
- **StatusFooter**: Shows model name, token count, and message count
- **Footer**: Displays keyboard shortcuts
- **Welcome Screen**: Centered welcome message with quick start guide
- **Session Picker**: Modal dialog for managing multiple sessions (Ctrl+S)

## Phases

- **Phase 1 (MVP)**: Basic chat with DeepSeek integration ✅
- **Phase 2 (Feature-Complete)**: Tools, streaming, persistence, multi-session ✅
- **Phase 3 (Production-Ready)**: Multi-provider, export/import, caching, context compression ✅

## Quick Start

### Prerequisites
- Python 3.10+
- An API key from at least one supported provider

### Installation

```bash
pip install -e .
```

### Configuration

Create `~/.poplar/config.yaml`:

```yaml
language: en
provider: deepseek
providers:
  deepseek:
    api_key: sk-xxxxxxxxxxxx    # your DeepSeek API key
    model: deepseek-chat
```

Or set environment variables:

```bash
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx
export POPLAR_LANGUAGE=zh       # optional, for Chinese UI
```

### Usage

```bash
poplar
```

Or:

```bash
python -m poplar.main
```

### Keyboard Shortcuts

- `Enter` - Send message
- `Ctrl+Enter` - New line in input
- `Ctrl+S` - Open session picker (switch/create/delete/rename sessions)
- `Ctrl+C` - Copy last assistant response or click `copy` button on any message
- `Ctrl+Q` - Quit application
- `ESC` - Cancel ongoing API request

### Commands

Type these in the composer:
- `/help` — Show all available commands
- `/quit` — Exit application
- `/context` — Show session context info (token count, messages, compression status)
- `/compress` — Manually compress conversation via LLM summarization
- `/stats` — Show performance statistics
- `/session` — Open session picker
- `/clear` — Clear current session
- `/export <path>` — Export current session to JSON file
- `/import <path>` — Import session from JSON file
- `/provider` — Show current provider and model
- `/provider list` — List all available providers
- `/provider set <name>` — Switch provider at runtime

### Configuration Reference

Configuration file at `~/.poplar/config.yaml`:

```yaml
# Language: en (English) or zh (Chinese)
language: en

# Default provider: deepseek, openai, anthropic, or ollama
provider: deepseek

# Per-provider settings
providers:
  deepseek:
    api_key: sk-xxx              # or set via DEEPSEEK_API_KEY env
    model: deepseek-chat
  openai:
    api_key: sk-xxx              # or set via OPENAI_API_KEY env
    model: gpt-4o
  anthropic:
    api_key: sk-xxx              # or set via ANTHROPIC_API_KEY env
    model: claude-3-5-sonnet-20241022
  ollama:
    model: llama3
    base_url: http://localhost:11434  # no API key needed

# Cache settings
cache:
  enabled: true
  max_memory_items: 100
  tool_read_file_ttl: 300
  tool_list_dir_ttl: 30
  api_response_ttl: 3600

# Context compression settings
context:
  max_tokens: 32768
  auto_compress_at: 0.7
  keep_recent_exchanges: 3
  max_turns: 10
```

Environment variables:

```bash
# API keys
export DEEPSEEK_API_KEY=sk-...
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-...

# Language override
export POPLAR_LANGUAGE=zh
```

### Testing

```bash
pytest tests/ -v
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/

# Type check
mypy src/
```

## License

MIT
