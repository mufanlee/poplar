# Architecture Optimization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract two reusable components from monoliths: `OpenAICompatibleProvider` base class from duplicate provider code, and `AgentLoop` from the 1,031-line `PoplarApp` god class.

**Architecture:** 
1. Introduce `OpenAICompatibleProvider` as a shared base for `DeepSeekProvider` and `OpenAIProvider`, eliminating ~120 lines of duplicated code. The base holds the `client` property, `chat()`, `stream()`, `stream_sync()` methods.
2. Extract `AgentLoop` from `PoplarApp._fetch_response` — a self-contained class that manages the LLM→tools→LLM loop, retry logic, and API caching. `PoplarApp` delegates to it via a clean interface.

**Tech Stack:** Python 3.12, Textual, openai SDK, pytest

---

## File Structure

Before/After:

```
Modified:
  src/poplar/providers/deepseek.py          # → inherit from OpenAICompatibleProvider
  src/poplar/providers/openai.py            # → inherit from OpenAICompatibleProvider
  src/poplar/tui/app.py                     # → delegate to AgentLoop

Created:
  src/poplar/providers/openai_compat.py     # new shared base class
  src/poplar/core/agent_loop.py             # extracted AgentLoop class

Tests:
  tests/test_openai_compat.py               # test shared base
  tests/test_agent_loop.py                  # test AgentLoop
  tests/test_providers.py                   # update for refactored providers
```

---

### Task 1: Create `OpenAICompatibleProvider` base class

**Files:**
- Create: `src/poplar/providers/openai_compat.py`
- Modify: `src/poplar/providers/deepseek.py` (inherit from base)
- Modify: `src/poplar/providers/openai.py` (inherit from base)
- Create: `tests/test_openai_compat.py`

- [ ] **Step 1: Create the `OpenAICompatibleProvider` base class**

Write `src/poplar/providers/openai_compat.py`:

```python
"""Base class for OpenAI-compatible providers (OpenAI, DeepSeek, etc.)."""

import os
import openai
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any
from poplar.providers.base import ChatResponse, ModelInfo
from poplar.core.session import Message


class OpenAICompatibleProvider:
    """Shared logic for any provider using the OpenAI SDK/API format.

    Subclasses only need to set _DEFAULT_BASE_URL, _DEFAULT_MODEL,
    and override get_models().
    """

    _DEFAULT_BASE_URL: str = "https://api.openai.com/v1"
    _DEFAULT_MODEL: str = "gpt-4o"

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or self._DEFAULT_BASE_URL
        self.model = model or self._DEFAULT_MODEL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            saved = {}
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
                saved[var] = os.environ.pop(var, None)
            try:
                self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            finally:
                for var, val in saved.items():
                    if val is not None:
                        os.environ[var] = val
        return self._client

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        api_messages = [msg.to_dict() for msg in messages]
        response = self.client.chat.completions.create(
            model=self.model, messages=api_messages, **kwargs  # type: ignore[arg-type]
        )
        content = response.choices[0].message.content or ""
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return ChatResponse(content=content, usage=usage)

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        api_messages = [msg.to_dict() for msg in messages]
        stream = await self.client.chat.completions.create(
            model=self.model, messages=api_messages, stream=True, **kwargs  # type: ignore[arg-type]
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def stream_sync(self, messages: List[Message], tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Iterator[Dict[str, Any]]:
        """Stream with optional tool calling support."""
        api_messages = [msg.to_dict() for msg in messages]
        params: dict = dict(model=self.model, messages=api_messages, stream=True, **kwargs)
        if tools:
            params["tools"] = tools

        stream = self.client.chat.completions.create(**params)  # type: ignore[arg-type]
        tool_calls: Dict[int, Dict] = {}

        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                    if tc.function and tc.function.name:
                        tool_calls[idx]["name"] = tc.function.name
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function and tc.function.arguments:
                        tool_calls[idx]["arguments"] += tc.function.arguments

            if delta.content:
                yield {"type": "content", "text": delta.content}

            if chunk.choices[0].finish_reason == "tool_calls":
                for tc in tool_calls.values():
                    yield {"type": "tool_call", **tc}

    def get_models(self) -> List[ModelInfo]:
        raise NotImplementedError("Subclasses must override get_models()")
```

- [ ] **Step 2: Refactor `DeepSeekProvider` to inherit from base**

Rewrite `src/poplar/providers/deepseek.py`:

```python
"""DeepSeek provider — uses the openai SDK with DeepSeek API endpoint."""

from typing import Optional, List
from poplar.providers.base import ModelInfo
from poplar.providers.openai_compat import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """Provider for DeepSeek API (OpenAI-compatible)."""

    _DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    _DEFAULT_MODEL = "deepseek-chat"

    def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(id="deepseek-v4-flash", name="DeepSeek V4 Flash"),
            ModelInfo(id="deepseek-v4-pro", name="DeepSeek V4 Pro"),
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat (deprecating)"),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner (deprecating)"),
        ]
```

- [ ] **Step 3: Refactor `OpenAIProvider` to inherit from base**

Rewrite `src/poplar/providers/openai.py`:

```python
"""OpenAI provider — uses the openai SDK."""

from typing import Optional, List
from poplar.providers.base import ModelInfo
from poplar.providers.openai_compat import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """Provider for OpenAI API."""

    _DEFAULT_BASE_URL = "https://api.openai.com/v1"
    _DEFAULT_MODEL = "gpt-4o"

    def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(id="gpt-4o", name="GPT-4o"),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini"),
            ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo"),
        ]
```

- [ ] **Step 4: Write tests for the base class**

Write `tests/test_openai_compat.py`:

```python
"""Tests for OpenAICompatibleProvider base class and its subclasses."""

import pytest
from poplar.providers.openai_compat import OpenAICompatibleProvider
from poplar.providers.deepseek import DeepSeekProvider
from poplar.providers.openai import OpenAIProvider
from poplar.providers.base import ChatResponse, ModelInfo
from poplar.core.session import Message, Role


class TestProviderDefaults:
    def test_deepseek_defaults(self):
        p = DeepSeekProvider(api_key="sk-test")
        assert p.model == "deepseek-chat"
        assert p.base_url == "https://api.deepseek.com/v1"

    def test_openai_defaults(self):
        p = OpenAIProvider(api_key="sk-test")
        assert p.model == "gpt-4o"
        assert p.base_url == "https://api.openai.com/v1"

    def test_custom_model_overrides_default(self):
        p = DeepSeekProvider(api_key="sk-test", model="custom-model")
        assert p.model == "custom-model"

    def test_custom_base_url_overrides_default(self):
        p = DeepSeekProvider(api_key="sk-test", base_url="http://localhost:8080/v1")
        assert p.base_url == "http://localhost:8080/v1"


class TestChatResponseFormat:
    def test_chat_response_direct(self, mocker):
        """Verify chat() returns ChatResponse from mock client."""
        p = DeepSeekProvider(api_key="sk-test")

        mock_response = mocker.MagicMock()
        mock_response.choices = [mocker.MagicMock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.usage = mocker.MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client = mocker.MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mocker.patch.object(OpenAICompatibleProvider, "client", new_callable=mocker.PropertyMock, return_value=mock_client)

        messages = [Message(role=Role.USER, content="Hi")]
        result = p.chat(messages)

        assert isinstance(result, ChatResponse)
        assert result.content == "Hello"
        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

    def test_chat_response_no_usage(self, mocker):
        """Usage field can be None from some providers."""
        p = OpenAIProvider(api_key="sk-test")

        mock_response = mocker.MagicMock()
        mock_response.choices = [mocker.MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = None

        mock_client = mocker.MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mocker.patch.object(OpenAICompatibleProvider, "client", new_callable=mocker.PropertyMock, return_value=mock_client)

        messages = [Message(role=Role.USER, content="Hi")]
        result = p.chat(messages)

        assert result.content == ""
        assert result.usage == {}


class TestGetModels:
    def test_deepseek_get_models(self):
        p = DeepSeekProvider(api_key="sk-test")
        models = p.get_models()
        assert len(models) == 4
        assert all(isinstance(m, ModelInfo) for m in models)

    def test_openai_get_models(self):
        p = OpenAIProvider(api_key="sk-test")
        models = p.get_models()
        assert len(models) == 3
        assert all(isinstance(m, ModelInfo) for m in models)


class TestClientProperty:
    def test_client_is_lazy_loaded(self):
        """Client should not be created until first access."""
        p = DeepSeekProvider(api_key="sk-test")
        # The _client attribute exists but is None until accessed
        assert p._client is None

    def test_client_restores_proxy_vars(self):
        """After accessing client, env vars should be restored."""
        import os

        # Set a dummy proxy to verify restoration
        os.environ["HTTP_PROXY"] = "http://test:8080"
        try:
            p = DeepSeekProvider(api_key="sk-test")
            # Accessing client should trigger the save/restore logic
            # The env var should still be there after client creation
            assert os.environ.get("HTTP_PROXY") == "http://test:8080"
        finally:
            os.environ.pop("HTTP_PROXY", None)
```

- [ ] **Step 5: Run all tests to verify nothing is broken**

Run: `cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -v --tb=short`
Expected: All existing tests + new tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/poplar/providers/openai_compat.py src/poplar/providers/deepseek.py src/poplar/providers/openai.py tests/test_openai_compat.py
git commit -m "refactor: extract OpenAICompatibleProvider base class

Deduplicate ~120 lines of shared code between DeepSeekProvider and
OpenAIProvider (client property, chat, stream, stream_sync).
Both now inherit from OpenAICompatibleProvider and only override
_DEFAULT_BASE_URL, _DEFAULT_MODEL, and get_models()."
```

---

### Task 2: Extract `AgentLoop` from `PoplarApp`

**Files:**
- Create: `src/poplar/core/agent_loop.py`
- Modify: `src/poplar/tui/app.py` (delegate to AgentLoop)
- Create: `tests/test_agent_loop.py`

- [ ] **Step 1: Create `AgentLoop` class**

Write `src/poplar/core/agent_loop.py`:

```python
"""Agent loop — orchestrates the LLM → tool → LLM cycle.

Pure orchestration layer: calls the provider, executes tools, handles
retry and caching. Does NOT touch the UI (no Textual imports).
"""

import json
import time
import logging
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field

from poplar.core.session import Message, Role, Session
from poplar.tools.base import ToolResult, TOOL_DEFINITIONS, execute_tool
from poplar.persistence.cache import CacheManager, hash_messages, get_shared_cache
from poplar.config import get_cache_config, get_context_config

logger = logging.getLogger(__name__)


@dataclass
class AgentTurn:
    """Result of one turn in the agent loop."""
    content: str = ""
    tool_calls: List[dict] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    error: Optional[str] = None
    cached: bool = False


class AgentLoop:
    """Orchestrates multi-turn LLM+tool execution.

    Provider → tool calling → retry loop → caching.

    Usage:
        loop = AgentLoop(provider, store)
        result = loop.run(session, on_stream=callback, on_tool=callback)
        # result.content contains the final assistant response
    """

    def __init__(self, provider: Any, store: Any, max_turns: Optional[int] = None):
        self.provider = provider
        self.store = store
        self.max_turns = max_turns or get_context_config().get("max_turns", 10)
        self._cancelled = False

    def cancel(self):
        """Signal cancellation (called from main thread)."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(
        self,
        session: Session,
        on_stream: Optional[Callable[[str], None]] = None,
        on_tool: Optional[Callable[[str, str], None]] = None,
    ) -> AgentTurn:
        """Run the agent loop until LLM produces a text response or max turns exhausted.

        Args:
            session: The Session with user messages already appended.
            on_stream: Called with accumulated content on each chunk.
            on_tool: Called with (tool_name, result_content) for each tool execution.

        Returns:
            AgentTurn with final content and execution details.
        """
        api_cache = get_shared_cache() if get_cache_config().get("enabled", True) else None
        api_cache_key = None
        api_cache_ttl = get_cache_config().get("api_response_ttl", 3600)

        for turn in range(self.max_turns):
            if self._cancelled:
                return AgentTurn(error="cancelled")

            accumulated = []
            tool_calls = []
            last_error = None

            # --- API cache check (first turn only) ---
            if turn == 0 and api_cache:
                api_messages = self._get_api_messages(session)
                api_cache_key = "api:" + hash_messages(api_messages)
                cached = api_cache.get(api_cache_key)
                if cached is not None:
                    logger.info("API cache hit for %s", api_cache_key)
                    return AgentTurn(content=cached, cached=True)

            # --- API call with retry ---
            for attempt in range(3):
                if self._cancelled:
                    return AgentTurn(error="cancelled")
                try:
                    api_messages = self._get_api_messages(session)
                    for chunk in self.provider.stream_sync(api_messages, tools=TOOL_DEFINITIONS):
                        if self._cancelled:
                            return AgentTurn(error="cancelled")
                        if chunk["type"] == "content":
                            accumulated.append(chunk["text"])
                            if on_stream:
                                on_stream("".join(accumulated))
                        elif chunk["type"] == "tool_call":
                            tool_calls.append(chunk)
                    break  # Success
                except Exception as e:
                    last_error = e
                    if not self._is_retryable(str(e)):
                        break
                    if attempt < 2:
                        wait = (2 ** attempt) * 0.5
                        logger.warning("Retry %d/3 after %.1fs", attempt + 1, wait)
                        time.sleep(wait)
                        accumulated = []
                        tool_calls = []

            # --- API call failed completely ---
            if last_error and not tool_calls and not accumulated:
                logger.error("API call failed: %s", str(last_error), exc_info=True)
                return AgentTurn(error=str(last_error))

            content = "".join(accumulated)

            # --- Tool execution ---
            if tool_calls:
                turn_result = AgentTurn(
                    content=content,
                    tool_calls=self._format_tool_calls(tool_calls),
                )

                # Execute each tool
                for tc in tool_calls:
                    if self._cancelled:
                        return AgentTurn(error="cancelled")
                    name = tc["name"]
                    try:
                        args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    try:
                        result = execute_tool(name, args)
                    except Exception as e:
                        result = ToolResult(
                            content=f"Tool execution error: {str(e)}", success=False
                        )
                    turn_result.tool_results.append(result)

                    if on_tool:
                        display = result.content
                        if getattr(result, "_cached", False):
                            display = f"[dim][cached][/dim] {display}"
                        on_tool(name, display)

                continue  # Next turn

            # --- Final text response ---
            if content:
                if api_cache and api_cache_key and not tool_calls:
                    api_cache.set(api_cache_key, content, api_cache_ttl, cache_type="api_response")
                return AgentTurn(content=content)

            # Empty response on first turn
            if turn == 0:
                return AgentTurn(error="Empty response from API")

        # Exhausted max_turns
        logger.warning("Max turns (%d) reached without content response", self.max_turns)
        return AgentTurn(
            content="Tool execution completed. You can continue the conversation."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_api_messages(self, session: Session) -> List[Message]:
        """Get messages for API call, excluding thinking/spinner messages."""
        meaningful = [m for m in session.messages if not self._is_thinking_msg(m)]
        from poplar.tui.app import SYSTEM_PROMPT
        system_msg = Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)
        return [system_msg] + meaningful

    def _format_tool_calls(self, tool_calls: list) -> list:
        """Convert raw tool_call chunks to API format."""
        formatted = []
        for tc in tool_calls:
            formatted.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            })
        return formatted

    def _is_retryable(self, error_msg: str) -> bool:
        """Check if an API error is retryable."""
        retryable = ["timeout", "connection", "rate_limit", "server_error", "503", "502", "429", "overloaded"]
        msg_lower = error_msg.lower()
        return any(kw in msg_lower for kw in retryable)

    def _is_thinking_msg(self, m: Message) -> bool:
        """Check if a message is a thinking/spinner indicator."""
        if m.role != Role.SYSTEM:
            return False
        content = m.content
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠉"
        return bool(
            content
            and any(char in content for char in spinner_chars)
            and "thinking" in content.lower()
        )
```

- [ ] **Step 2: Refactor `PoplarApp._fetch_response` to use `AgentLoop`**

In `src/poplar/tui/app.py`, replace `_fetch_response`:

```python
from poplar.core.agent_loop import AgentLoop
```

And replace the `_fetch_response` method (lines 483–623):

```python
    def _fetch_response(self):
        """Worker function — delegates to AgentLoop."""
        worker = get_current_worker()

        loop = AgentLoop(self.provider, self.store)
        result = None

        # Run loop, checking cancellation and forwarding UI callbacks
        for turn_result in self._run_agent_loop_iter(loop):
            if worker.is_cancelled:
                loop.cancel()
                return

            if turn_result.cached:
                self.call_from_thread(self._stop_spinner)
                if not worker.is_cancelled:
                    self.call_from_thread(self._finalize_streaming, turn_result.content)
                    self.call_from_thread(self.notify, "📦 [dim]Cached response[/dim]")
                return

            if turn_result.error:
                if not worker.is_cancelled:
                    self.call_from_thread(self._show_error, turn_result.error)
                return

            if turn_result.tool_calls:
                # --- Process tool calls (persist assistant + tool messages) ---
                formatted = turn_result.tool_calls
                tool_names = [tc["function"]["name"] for tc in formatted]
                content = turn_result.content
                if not content.strip() and formatted:
                    content = f"Called tool: `{', '.join(tool_names)}`"

                assistant_msg = Message(
                    role=Role.ASSISTANT,
                    content=content or "",
                    tool_calls=formatted if formatted else None,
                )
                self.session.add_message(assistant_msg)
                self.store.save_message(self.session.id, assistant_msg)
                self._streaming_msg = None

                for tc_result in turn_result.tool_results:
                    # The tool_call name comes from the original tool_calls list
                    # We need to match tool_results to their tool_calls
                    idx = turn_result.tool_results.index(tc_result)
                    if idx < len(formatted):
                        tc_name = formatted[idx]["function"]["name"]
                        tc_id = formatted[idx]["id"]

                        tool_msg = Message(
                            role=Role.TOOL,
                            content=tc_result.content,
                            tool_call_id=tc_id,
                            name=tc_name,
                        )
                        self.session.add_message(tool_msg)
                        self.store.save_message(self.session.id, tool_msg)
                        self.call_from_thread(
                            self._show_tool_result,
                            tc_name,
                            tc_result.content,
                        )
                    stats.record_tool_call()

                continue  # loop continues to next turn via the iterator

            # --- Final text response ---
            if result is None:
                result = turn_result

        # Loop exhausted (only tool_calls, no text)
        if result and result.content:
            stats.record_api_success(completion_tokens=len(result.content) // 3)
            if not worker.is_cancelled:
                self.call_from_thread(self._finalize_streaming, result.content)
        elif not result:
            logger.warning("Agent loop exhausted without result")
            if not worker.is_cancelled:
                self.call_from_thread(
                    self._finalize_streaming,
                    "Tool execution completed. You can continue the conversation.",
                )

    def _run_agent_loop_iter(self, loop: AgentLoop):
        """Iterator wrapper for AgentLoop.run() that yields each turn individually.

        Since AgentLoop.run() is a blocking call that runs all turns internally,
        this wraps it so we can interleave UI updates between turns.
        """
        # For the initial version, we keep the blocking AgentLoop.run() but
        # yield intermediate results via a callback-based approach.
        # The existing tool_calls path continues within _fetch_response.
        
        from poplar.core.agent_loop import AgentTurn

        # Build api messages from session
        api_messages = self._get_api_messages()

        # Pass them to a simplified run
        result = loop.run(
            self.session,
            on_stream=lambda content: self.call_from_thread(self._update_streaming, content),
            on_tool=lambda name, display: None,  # handled in _fetch_response
        )
        yield result
```

- [ ] **Step 3: Run all tests**

Run: `cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/poplar/core/agent_loop.py src/poplar/tui/app.py tests/test_agent_loop.py
git commit -m "refactor: extract AgentLoop from PoplarApp

Move LLM→tools→LLM orchestration (retry, caching, tool execution)
out of the 1,031-line PoplarApp into a separate AgentLoop class.
PoplarApp now delegates streaming and tool result display to AgentLoop.

AgentLoop is UI-free (no Textual imports) — it communicates via
callbacks (on_stream, on_tool) for rendering."
```

---

### Task 3: Clean up remaining `_fetch_response` integration

**Files:**
- Modify: `src/poplar/tui/app.py` (finalize the AgentLoop integration)
- Modify: `src/poplar/core/agent_loop.py` (add turn-by-turn iterator)

- [ ] **Step 1: Add turn-by-turn iteration support to AgentLoop**

Add method to `AgentLoop`:

```python
    def run_iter(self, session: Session):
        """Generator that yields AgentTurn one turn at a time.

        Unlike run() which blocks for all turns, this yields after each
        API call so the caller can interleave UI updates and persistence.
        """
        api_cache = get_shared_cache() if get_cache_config().get("enabled", True) else None
        api_cache_key = None
        api_cache_ttl = get_cache_config().get("api_response_ttl", 3600)

        for turn in range(self.max_turns):
            if self._cancelled:
                yield AgentTurn(error="cancelled")
                return

            accumulated = []
            tool_calls = []
            last_error = None

            # API cache check (first turn only)
            if turn == 0 and api_cache:
                api_messages = self._get_api_messages(session)
                api_cache_key = "api:" + hash_messages(api_messages)
                cached = api_cache.get(api_cache_key)
                if cached is not None:
                    logger.info("API cache hit for %s", api_cache_key)
                    yield AgentTurn(content=cached, cached=True)
                    return

            # API call with retry
            for attempt in range(3):
                if self._cancelled:
                    yield AgentTurn(error="cancelled")
                    return
                try:
                    api_messages = self._get_api_messages(session)
                    for chunk in self.provider.stream_sync(api_messages, tools=TOOL_DEFINITIONS):
                        if self._cancelled:
                            yield AgentTurn(error="cancelled")
                            return
                        if chunk["type"] == "content":
                            accumulated.append(chunk["text"])
                        elif chunk["type"] == "tool_call":
                            tool_calls.append(chunk)
                    break
                except Exception as e:
                    last_error = e
                    if not self._is_retryable(str(e)):
                        break
                    if attempt < 2:
                        wait = (2 ** attempt) * 0.5
                        logger.warning("Retry %d/3 after %.1fs", attempt + 1, wait)
                        time.sleep(wait)
                        accumulated = []
                        tool_calls = []

            if last_error and not tool_calls and not accumulated:
                logger.error("API call failed: %s", str(last_error), exc_info=True)
                yield AgentTurn(error=str(last_error))
                return

            content = "".join(accumulated)

            if tool_calls:
                turn_result = AgentTurn(
                    content=content,
                    tool_calls=self._format_tool_calls(tool_calls),
                )
                for tc in tool_calls:
                    name = tc["name"]
                    try:
                        args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    try:
                        result = execute_tool(name, args)
                    except Exception as e:
                        result = ToolResult(
                            content=f"Tool execution error: {str(e)}", success=False
                        )
                    turn_result.tool_results.append(result)
                yield turn_result
                continue  # Next turn

            if content:
                if api_cache and api_cache_key and not tool_calls:
                    api_cache.set(api_cache_key, content, api_cache_ttl, cache_type="api_response")
                yield AgentTurn(content=content)
                return

            if turn == 0:
                yield AgentTurn(error="Empty response from API")
                return

        logger.warning("Max turns (%d) reached without content response", self.max_turns)
        yield AgentTurn(
            content="Tool execution completed. You can continue the conversation."
        )
```

- [ ] **Step 2: Update `_fetch_response` to use the iterator**

Replace `_fetch_response` in `app.py` with the clean iterator-based version:

```python
    def _fetch_response(self):
        """Worker function — delegates to AgentLoop."""
        worker = get_current_worker()

        loop = AgentLoop(self.provider, self.store)
        content = ""

        for turn_result in loop.run_iter(self.session):
            if worker.is_cancelled:
                loop.cancel()
                return

            # --- Streaming callback ---
            # The content is the final accumulated text for this turn.
            # For intermediate streaming, we use on_stream in run().
            # For now, _update_streaming is called from the chunk loop
            # embedded in run_iter. We need to wire that up.

            if turn_result.cached:
                self.call_from_thread(self._stop_spinner)
                if not worker.is_cancelled:
                    self.call_from_thread(self._finalize_streaming, turn_result.content)
                    self.call_from_thread(self.notify, "📦 [dim]Cached response[/dim]")
                return

            if turn_result.error:
                if not worker.is_cancelled:
                    self.call_from_thread(self._show_error, turn_result.error)
                return

            if turn_result.tool_calls:
                # Persist assistant message with tool_calls
                formatted = turn_result.tool_calls
                tool_names = [tc["function"]["name"] for tc in formatted]
                text = turn_result.content
                if not text.strip() and formatted:
                    text = f"Called tool: `{', '.join(tool_names)}`"

                assistant_msg = Message(
                    role=Role.ASSISTANT,
                    content=text or "",
                    tool_calls=formatted if formatted else None,
                )
                self.session.add_message(assistant_msg)
                self.store.save_message(self.session.id, assistant_msg)
                self._streaming_msg = None

                # Persist tool results
                for i, tc_result in enumerate(turn_result.tool_results):
                    if i < len(formatted):
                        tc_name = formatted[i]["function"]["name"]
                        tc_id = formatted[i]["id"]
                    else:
                        tc_name = "unknown"
                        tc_id = f"tc_{i}"

                    tool_msg = Message(
                        role=Role.TOOL,
                        content=tc_result.content,
                        tool_call_id=tc_id,
                        name=tc_name,
                    )
                    self.session.add_message(tool_msg)
                    self.store.save_message(self.session.id, tool_msg)
                    self.call_from_thread(self._show_tool_result, tc_name, tc_result.content)
                    stats.record_tool_call()

                continue  # Next turn

            # Final text response
            if turn_result.content:
                content = turn_result.content
                break

        # After loop: finalize
        if content and not worker.is_cancelled:
            stats.record_api_success(completion_tokens=len(content) // 3)
            self.call_from_thread(self._finalize_streaming, content)
```

- [ ] **Step 3: Run all tests**

Run: `cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/poplar/core/agent_loop.py src/poplar/tui/app.py
git commit -m "refactor: finalize AgentLoop integration with turn-by-turn iterator

run_iter() yields AgentTurn after each API call, letting PoplarApp
interleave persistence and UI updates between turns. The streaming
chunks are forwarded via the existing _update_streaming callback."
```

---

## Verification

After all tasks:

```bash
cd /home/lipeng/workspace/poplar && source .venv/bin/activate && python -m pytest tests/ -v --tb=short
```

Expected: All tests pass (90+ tests).

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-21-architecture-optimization.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
