# Poplar

AI Agent TUI application built with Python and Textual framework.

## Overview

Poplar (杨树) is a terminal-based AI chat application built with Python and Textual framework. It features a rich terminal user interface with DeepSeek API integration, supporting both English and Chinese languages.

## Features

### Core Features
- **Rich TUI Interface**: Built with Textual framework, featuring rounded borders, themed scrollbars, and message bubbles
- **DeepSeek Integration**: Connect to DeepSeek API for AI-powered conversations
- **Streaming Responses**: Token-by-token real-time display of AI responses
- **Tool Execution**: Built-in tools for file read/write, directory listing, and shell commands — multi-turn automatic execution
- **Multi-Session Management**: Create, switch, delete, and rename sessions (Ctrl+S)
- **SQLite Persistence**: Conversations survive application restart
- **Markdown Rendering**: Assistant responses support Markdown formatting
- **Multi-line Input**: TextArea with Ctrl+Enter for new lines
- **Message Queuing**: Continue typing while waiting — messages auto-send after response
- **Request Cancellation**: Press ESC to cancel ongoing API requests
- **API Retry**: Automatic retry with exponential backoff on failures
- **Copy Response**: Ctrl+C to copy the last assistant response
- **Internationalization**: Support for English and Chinese languages
- **Configuration Management**: YAML-based configuration file with model and language settings

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
- **Phase 3 (Production-Ready)**: Plugins, multi-provider, advanced features

## Quick Start (Phase 1 - MVP)

### Prerequisites
- Python 3.10+
- DeepSeek API key

### Installation

```bash
pip install -e .
```

### Configuration

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

Or set environment variable:

```bash
export DEEPSEEK_API_KEY=your-api-key-here
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
- `Ctrl+C` - Copy last assistant response
- `Ctrl+Q` - Quit application
- `ESC` - Cancel ongoing API request

### Configuration

Configuration file is automatically created at `~/.poplar/config.yaml` on first run:

```yaml
# Language: en (English) or zh (Chinese)
language: en

# Model: deepseek-chat or deepseek-coder
model: deepseek-chat
```

You can also use environment variables:

```bash
# Switch language
export POPLAR_LANGUAGE=zh

# Set API key
export DEEPSEEK_API_KEY=your-api-key-here
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
