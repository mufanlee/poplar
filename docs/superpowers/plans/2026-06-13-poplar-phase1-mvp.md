# Poplar Phase 1 (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working TUI chat interface that can send messages to DeepSeek API and display responses.

**Architecture:** Minimal layered architecture with Textual TUI, simple DeepSeek provider integration, and in-memory session management. No persistence, no tools, no sub-agents in MVP.

**Tech Stack:** Python 3.10+, Textual 0.50+, OpenAI SDK 1.0+

---

## File Structure Overview

Files to be created for Phase 1:

```
poplar/
├── src/poplar/
│   ├── __init__.py                    # Already exists
│   ├── main.py                        # Exists, needs update
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py                     # Main Textual application
│   │   ├── chat_view.py               # Chat display component
│   │   └── composer.py                # Message input component
│   ├── core/
│   │   ├── __init__.py
│   │   └── session.py                 # In-memory session management
│   └── providers/
│       ├── __init__.py
│       ├── base.py                    # Provider interface
│       └── deepseek.py                # DeepSeek provider implementation
├── tests/
│   ├── __init__.py
│   ├── test_session.py
│   └── test_deepseek_provider.py
└── examples/
    └── config.example.yaml            # Already exists
```

---

### Task 1: Project Setup and Dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `src/poplar/tui/__init__.py`
- Create: `src/poplar/core/__init__.py`
- Create: `src/poplar/providers/__init__.py`

- [x] **Step 1: Update pyproject.toml with dependencies**

Read current file and verify dependencies are correct:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "poplar"
version = "0.1.0"
description = "AI Agent TUI application built with Textual"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "textual>=0.50.0",
    "openai>=1.0.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
]

[project.scripts]
poplar = "poplar.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 88
target-version = ['py310']

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

- [x] **Step 2: Create package init files**

Create `tests/__init__.py`:
```python
```

Create `src/poplar/tui/__init__.py`:
```python
```

Create `src/poplar/core/__init__.py`:
```python
```

Create `src/poplar/providers/__init__.py`:
```python
```

- [x] **Step 3: Install dependencies**

Run: `pip install -e ".[dev]"`
Expected: All dependencies installed successfully

- [x] **Step 4: Verify installation**

Run: `python -c "import textual; print(textual.__version__)"`
Expected: Version number >= 0.50.0

Run: `python -c "import openai; print(openai.__version__)"`
Expected: Version number >= 1.0.0

- [x] **Step 5: Commit**

```bash
git add pyproject.toml tests/__init__.py src/poplar/tui/__init__.py src/poplar/core/__init__.py src/poplar/providers/__init__.py
git commit -m "chore: set up project structure and dependencies"
```

---

### Task 2: Define Core Data Models

**Files:**
- Create: `src/poplar/core/session.py`
- Test: `tests/test_session.py`

- [x] **Step 1: Write failing test for Message model**

Create `tests/test_session.py`:

```python
from poplar.core.session import Message, Role


def test_message_creation():
    msg = Message(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"


def test_message_to_dict():
    msg = Message(role=Role.USER, content="Test")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "Test"}
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session.py::test_message_creation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'poplar.core.session'"

- [x] **Step 3: Implement Message and Role models**

Create `src/poplar/core/session.py`:

```python
from dataclasses import dataclass, asdict
from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: Role
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role.value, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(role=Role(data["role"]), content=data["content"])
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session.py::test_message_creation tests/test_session.py::test_message_to_dict -v`
Expected: Both tests PASS

- [x] **Step 5: Add Session class test**

Add to `tests/test_session.py`:

```python
from poplar.core.session import Session


def test_session_creation():
    session = Session(id="test-1", title="Test Session")
    assert session.id == "test-1"
    assert session.title == "Test Session"
    assert len(session.messages) == 0


def test_session_add_message():
    session = Session(id="test-1", title="Test")
    msg = Message(role=Role.USER, content="Hello")
    session.add_message(msg)
    assert len(session.messages) == 1
    assert session.messages[0].content == "Hello"
```

- [x] **Step 6: Implement Session class**

Add to `src/poplar/core/session.py`:

```python
from typing import List
from datetime import datetime


@dataclass
class Session:
    id: str
    title: str
    messages: List[Message] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_messages_for_api(self) -> List[dict]:
        return [msg.to_dict() for msg in self.messages]
```

- [x] **Step 7: Run all session tests**

Run: `pytest tests/test_session.py -v`
Expected: All 4 tests PASS

- [x] **Step 8: Commit**

```bash
git add src/poplar/core/session.py tests/test_session.py
git commit -m "feat: add core data models (Message, Role, Session)"
```

---

### Task 3: Create Provider Interface

**Files:**
- Create: `src/poplar/providers/base.py`
- Test: `tests/test_deepseek_provider.py` (interface test only)

- [x] **Step 1: Write test for Provider protocol**

Create `tests/test_deepseek_provider.py`:

```python
from poplar.providers.base import Provider
from poplar.core.session import Message, Role


def test_provider_interface_exists():
    """Verify Provider protocol is defined."""
    from poplar.providers.base import Provider
    assert Provider is not None


def test_provider_has_required_methods():
    """Verify Provider protocol has chat and stream methods."""
    import inspect
    from poplar.providers.base import Provider

    # Check that Protocol defines the methods
    assert hasattr(Provider, 'chat') or 'chat' in dir(Provider)
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_deepseek_provider.py::test_provider_interface_exists -v`
Expected: FAIL with "ModuleNotFoundError"

- [x] **Step 3: Implement Provider protocol**

Create `src/poplar/providers/base.py`:

```python
from typing import Protocol, List, AsyncIterator
from poplar.core.session import Message


class ChatResponse:
    def __init__(self, content: str, usage: dict = None):
        self.content = content
        self.usage = usage or {}


class ModelInfo:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class Provider(Protocol):
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        """Send messages and get response."""
        ...

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream response chunks."""
        ...

    def get_models(self) -> List[ModelInfo]:
        """Get available models."""
        ...
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_deepseek_provider.py -v`
Expected: Tests PASS

- [x] **Step 5: Commit**

```bash
git add src/poplar/providers/base.py tests/test_deepseek_provider.py
git commit -m "feat: define Provider protocol interface"
```

---

### Task 4: Implement DeepSeek Provider

**Files:**
- Create: `src/poplar/providers/deepseek.py`
- Modify: `tests/test_deepseek_provider.py` (add integration tests)

- [x] **Step 1: Write failing test for DeepSeek provider initialization**

Add to `tests/test_deepseek_provider.py`:

```python
from poplar.providers.deepseek import DeepSeekProvider


def test_deepseek_provider_creation():
    provider = DeepSeekProvider(api_key="test-key")
    assert provider.api_key == "test-key"
    assert provider.base_url == "https://api.deepseek.com/v1"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_deepseek_provider.py::test_deepseek_provider_creation -v`
Expected: FAIL with "ModuleNotFoundError"

- [x] **Step 3: Implement DeepSeekProvider**

Create `src/poplar/providers/deepseek.py`:

```python
import openai
from typing import List, AsyncIterator
from poplar.providers.base import Provider, ChatResponse, ModelInfo
from poplar.core.session import Message


class DeepSeekProvider:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        """Send messages to DeepSeek and get response."""
        api_messages = [msg.to_dict() for msg in messages]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            **kwargs
        )

        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return ChatResponse(content=content, usage=usage)

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream response from DeepSeek."""
        api_messages = [msg.to_dict() for msg in messages]

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_models(self) -> List[ModelInfo]:
        """Return available DeepSeek models."""
        return [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat"),
            ModelInfo(id="deepseek-coder", name="DeepSeek Coder"),
        ]
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_deepseek_provider.py::test_deepseek_provider_creation -v`
Expected: PASS

- [x] **Step 5: Add unit test for chat method (mocked)**

Add to `tests/test_deepseek_provider.py`:

```python
from unittest.mock import Mock, patch
from poplar.core.session import Message, Role


def test_deepseek_chat_mocked():
    """Test chat method without actual API call."""
    with patch('openai.OpenAI') as mock_client:
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.return_value.chat.completions.create.return_value = mock_response

        # Test
        provider = DeepSeekProvider(api_key="test-key")
        messages = [Message(role=Role.USER, content="Hello")]
        response = provider.chat(messages)

        assert response.content == "Test response"
        assert response.usage["total_tokens"] == 15
```

- [x] **Step 6: Run mocked test**

Run: `pytest tests/test_deepseek_provider.py::test_deepseek_chat_mocked -v`
Expected: PASS

- [x] **Step 7: Commit**

```bash
git add src/poplar/providers/deepseek.py tests/test_deepseek_provider.py
git commit -m "feat: implement DeepSeek provider with OpenAI SDK"
```

---

### Task 5: Build ChatView Component

**Files:**
- Create: `src/poplar/tui/chat_view.py`

- [x] **Step 1: Create basic ChatView widget**

Create `src/poplar/tui/chat_view.py`:

```python
from textual.widget import Widget
from textual.reactive import reactive
from poplar.core.session import Message, Role


class ChatView(Widget):
    """Displays conversation history."""

    messages: reactive[list] = reactive([])

    def render(self) -> str:
        if not self.messages:
            return "No messages yet. Start a conversation!"

        lines = []
        for msg in self.messages:
            if msg.role == Role.USER:
                lines.append(f"[bold blue]You:[/bold blue] {msg.content}")
            elif msg.role == Role.ASSISTANT:
                lines.append(f"[bold green]Assistant:[/bold green] {msg.content}")
            elif msg.role == Role.SYSTEM:
                lines.append(f"[dim]System: {msg.content}[/dim]")
            lines.append("")  # Empty line between messages

        return "\n".join(lines)

    def add_message(self, message: Message):
        self.messages = self.messages + [message]
```

- [x] **Step 2: Verify ChatView imports correctly**

Run: `python -c "from poplar.tui.chat_view import ChatView; print('OK')"`
Expected: "OK"

- [x] **Step 3: Commit**

```bash
git add src/poplar/tui/chat_view.py
git commit -m "feat: create ChatView widget for displaying messages"
```

---

### Task 6: Build Composer Component

**Files:**
- Create: `src/poplar/tui/composer.py`

- [x] **Step 1: Create basic Composer widget**

Create `src/poplar/tui/composer.py`:

```python
from textual.widget import Widget
from textual.widgets import TextArea
from textual.message import Message


class ComposerSubmit(Message):
    """Message sent when user submits input."""
    def __init__(self, text: str):
        self.text = text
        super().__init__()


class Composer(Widget):
    """Multi-line input field for user messages."""

    def compose(self):
        self.text_area = TextArea(id="input")
        yield self.text_area

    def on_key(self, event):
        if event.key == "enter" and not event.shift:
            event.prevent_default()
            text = self.text_area.text
            if text.strip():
                self.post_message(ComposerSubmit(text=text))
                self.text_area.text = ""
```

- [x] **Step 2: Verify Composer imports correctly**

Run: `python -c "from poplar.tui.composer import Composer, ComposerSubmit; print('OK')"`
Expected: "OK"

- [x] **Step 3: Commit**

```bash
git add src/poplar/tui/composer.py
git commit -m "feat: create Composer widget for user input"
```

---

### Task 7: Assemble Main TUI Application

**Files:**
- Create: `src/poplar/tui/app.py`
- Modify: `src/poplar/main.py`

- [x] **Step 1: Create basic TUI app**

Create `src/poplar/tui/app.py`:

```python
from textual.app import App, ComposeResult
from poplar.tui.chat_view import ChatView
from poplar.tui.composer import Composer, ComposerSubmit
from poplar.core.session import Session, Message, Role
from poplar.providers.deepseek import DeepSeekProvider
import os


class PoplarApp(App):
    """Main Poplar TUI application."""

    CSS = """
    ChatView {
        height: 80%;
        border: solid green;
    }

    Composer {
        height: 20%;
        border: solid blue;
    }
    """

    def __init__(self):
        super().__init__()
        self.session = Session(id="default", title="New Chat")
        api_key = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
        self.provider = DeepSeekProvider(api_key=api_key)

    def compose(self) -> ComposeResult:
        yield ChatView(id="chat")
        yield Composer(id="composer")

    def on_composer_submit(self, event: ComposerSubmit):
        """Handle user message submission."""
        # Add user message to session
        user_msg = Message(role=Role.USER, content=event.text)
        self.session.add_message(user_msg)

        # Update chat view
        chat_view = self.query_one(ChatView)
        chat_view.add_message(user_msg)

        # Get response from provider
        try:
            response = self.provider.chat(self.session.messages)
            assistant_msg = Message(role=Role.ASSISTANT, content=response.content)
            self.session.add_message(assistant_msg)
            chat_view.add_message(assistant_msg)
        except Exception as e:
            error_msg = Message(role=Role.ASSISTANT, content=f"Error: {str(e)}")
            self.session.add_message(error_msg)
            chat_view.add_message(error_msg)
```

- [x] **Step 2: Update main.py to launch app**

Modify `src/poplar/main.py`:

```python
"""Poplar - AI Agent TUI Application"""

import sys
import os


def main():
    """Main entry point for Poplar."""
    from poplar.tui.app import PoplarApp

    # Check for API key
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Warning: DEEPSEEK_API_KEY environment variable not set.")
        print("Set it or edit src/poplar/tui/app.py to add your API key.")

    app = PoplarApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 3: Test app launches (without API key)**

Run: `DEEPSEEK_API_KEY=test python -m poplar.main`
Expected: TUI app opens with empty chat view and composer

Press `q` to quit.

- [x] **Step 4: Commit**

```bash
git add src/poplar/tui/app.py src/poplar/main.py
git commit -m "feat: assemble main TUI application with ChatView and Composer"
```

---

### Task 8: Integration Test and Documentation

**Files:**
- Modify: `README.md`
- Create: `.env.example`

- [x] **Step 1: Create .env.example**

Create `.env.example`:

```bash
# DeepSeek API Key
# Get yours at https://platform.deepseek.com
DEEPSEEK_API_KEY=your-api-key-here
```

- [x] **Step 2: Update README with usage instructions**

Modify `README.md` to add:

```markdown
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
```

- [x] **Step 3: Manual integration test**

1. Set API key: `export DEEPSEEK_API_KEY=your-actual-key`
2. Run: `poplar`
3. Type a message and press Enter
4. Verify response appears
5. Press `q` to quit

- [x] **Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [x] **Step 5: Final commit**

```bash
git add README.md .env.example
git commit -m "docs: add quick start guide and configuration example"
```

---

## Phase 1 Success Criteria Checklist

- [x] Can send message and receive response from DeepSeek API
- [x] Conversation persists during session (in memory)
- [x] Clean shutdown without data loss (press `q`)
- [x] All tests pass
- [x] Basic documentation complete

## Next Steps (Phase 2)

After completing Phase 1, the next phase will add:
- SQLite persistence
- Tool execution (file ops, shell commands)
- Streaming responses
- Multiple session support
- Sidebar UI
- Status bar
- Sub-agent routing

Plan complete and saved to `docs/superpowers/plans/2026-06-13-poplar-phase1-mvp.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
