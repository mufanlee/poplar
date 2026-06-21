"""Agent loop — orchestrates the LLM → tool → LLM cycle.

Pure orchestration layer: calls the provider, executes tools, handles
retry and caching. Does NOT touch the UI (no Textual imports).
"""

import json
import time
import logging
from typing import Optional, List, Callable, Dict, Any

from dataclasses import dataclass, field

from poplar.core.session import Message, Role, Session
from poplar.tools.base import ToolResult, TOOL_DEFINITIONS, execute_tool
from poplar.persistence.cache import hash_messages, get_shared_cache
from poplar.config import get_cache_config, get_context_config
from poplar.utils import SPINNER_CHARS, is_thinking_message

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Poplar, a TUI-based AI assistant with tool execution "
    "capabilities. You can read/write files, list directories, and "
    "run shell commands. Be concise and helpful."
)


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
        loop = AgentLoop(provider, max_turns=10)
        for turn_result in loop.run_iter(session):
            if turn_result.error:
                handle_error(turn_result.error)
            elif turn_result.cached:
                handle_cached(turn_result.content)
            elif turn_result.tool_calls:
                # Persist assistant + tool messages, then loop continues
                persist_tool_calls(turn_result)
                # Next iteration = next turn
            else:
                # Final text response
                handle_response(turn_result.content)
                break
    """

    def __init__(self, provider, max_turns: Optional[int] = None):
        self.provider = provider
        self.max_turns = max_turns or get_context_config().get("max_turns", 10)
        self._cancelled = False

    def cancel(self):
        """Signal cancellation (called from main thread)."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run_iter(self, session: Session, on_stream: Optional[Callable[[str], None]] = None):
        """Generator that yields AgentTurn one turn at a time.

        Unlike a blocking run() which would run all turns internally,
        this yields after each API call so the caller can interleave
        UI updates, persistence, and cancellation checks between turns.

        Args:
            session: The current conversation session.
            on_stream: Optional callback called with accumulated content
                       as streaming chunks arrive.
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

            # --- API cache check (first turn only) ---
            if turn == 0 and api_cache:
                api_messages = self._get_api_messages(session)
                api_cache_key = "api:" + hash_messages(api_messages)
                cached = api_cache.get(api_cache_key)
                if cached is not None:
                    logger.info("API cache hit for %s", api_cache_key)
                    yield AgentTurn(content=cached, cached=True)
                    return

            # --- API call with retry ---
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
                yield AgentTurn(error=str(last_error))
                return

            content = "".join(accumulated)

            # --- Tool execution ---
            if tool_calls:
                turn_result = AgentTurn(
                    content=content,
                    tool_calls=self._format_tool_calls(tool_calls),
                )

                # Execute each tool and collect results
                for tc in tool_calls:
                    if self._cancelled:
                        yield AgentTurn(error="cancelled")
                        return
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
                continue  # Next turn — caller persists messages then loops

            # --- Final text response ---
            if content:
                if api_cache and api_cache_key and not tool_calls:
                    api_cache.set(api_cache_key, content, api_cache_ttl, cache_type="api_response")
                yield AgentTurn(content=content)
                return

            # Empty response on first turn
            if turn == 0:
                yield AgentTurn(error="Empty response from API")
                return

        # Exhausted max_turns — model returned only tool_calls, no text
        logger.warning("Max turns (%d) reached without content response", self.max_turns)
        yield AgentTurn(
            content="Tool execution completed. You can continue the conversation."
        )

    # ------------------------------------------------------------------
    # Helpers (moved from PoplarApp)
    # ------------------------------------------------------------------

    def _get_api_messages(self, session: Session) -> List[Message]:
        """Get messages for API call, excluding thinking/spinner messages."""
        meaningful = [m for m in session.messages if not is_thinking_message(m)]
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

    @staticmethod
    def _is_retryable(error_msg: str) -> bool:
        """Check if an API error is retryable."""
        not_retryable = ["400", "401", "402", "422", "invalid", "auth",
                         "authentication", "balance", "insufficient"]
        msg_lower = error_msg.lower()
        if any(kw in msg_lower for kw in not_retryable):
            return False
        retryable = ["timeout", "connection", "rate_limit", "server_error",
                     "429", "500", "502", "503", "overloaded", "busy"]
        return any(kw in msg_lower for kw in retryable)

