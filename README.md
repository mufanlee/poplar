# Poplar

AI Agent TUI application built with Python and Textual framework.

## Overview

Poplar (杨树) is a terminal-based AI chat application built with Python and Textual framework. It features a rich terminal user interface with DeepSeek API integration, supporting both English and Chinese languages.

## Features

### Core Features
- **Rich TUI Interface**: Built with Textual framework, featuring rounded borders, themed scrollbars, and message bubbles
- **DeepSeek Integration**: Connect to DeepSeek API for AI-powered conversations
- **Markdown Rendering**: Assistant responses support Markdown formatting
- **Real-time Animation**: Spinner animation with elapsed time display during API calls
- **Request Cancellation**: Press ESC to cancel ongoing API requests
- **Internationalization**: Support for English and Chinese languages
- **Configuration Management**: YAML-based configuration file with model selection

### UI Components
- **Header**: Displays application title "🌳 Poplar" and clock
- **ChatView**: Scrollable message display area with message bubbles
- **Composer**: User input field with placeholder text
- **StatusFooter**: Shows model name, token count, and message count
- **Footer**: Displays keyboard shortcuts
- **Welcome Screen**: Centered welcome message with quick start guide

## Phases

- **Phase 1 (MVP)**: Basic chat with DeepSeek integration
- **Phase 2 (Feature-Complete)**: Tools, sub-agents, persistence
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
