# Poplar

AI Agent TUI application built with Python and Textual framework.

## Overview

Poplar is a terminal-based AI agent that helps you with coding tasks, file operations, and more. It supports multiple AI providers and features a rich terminal user interface.

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
- `Shift+Enter` - New line
- `q` - Quit application

### Testing

```bash
pytest tests/ -v
```

## Configuration (Advanced)

Create `~/.config/poplar/config.yaml`:

```yaml
providers:
  deepseek:
    api_key: "your-api-key"
    base_url: "https://api.deepseek.com/v1"
    default_model: "deepseek-chat"
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
