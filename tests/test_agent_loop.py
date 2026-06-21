"""Tests for AgentLoop — the LLM+tool orchestration class."""

from unittest.mock import MagicMock, patch
from poplar.core.agent_loop import AgentLoop, AgentTurn
from poplar.utils import SPINNER_CHARS, is_thinking_message
from poplar.core.session import Session, Message, Role
from poplar.tools.base import ToolResult

# Pick a real spinner char for tests
SPINNER = SPINNER_CHARS[0]


class TestAgentTurn:
    def test_default_agent_turn(self):
        turn = AgentTurn()
        assert turn.content == ""
        assert turn.tool_calls == []
        assert turn.tool_results == []
        assert turn.error is None
        assert turn.cached is False

    def test_agent_turn_with_content(self):
        turn = AgentTurn(content="Hello world")
        assert turn.content == "Hello world"

    def test_agent_turn_with_error(self):
        turn = AgentTurn(error="timeout")
        assert turn.error == "timeout"

    def test_agent_turn_with_tool_calls(self):
        turn = AgentTurn(
            content="Let me check",
            tool_calls=[
                {
                    "id": "c1",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path":"test.txt"}',
                    },
                }
            ],
            tool_results=[ToolResult(content="file contents")],
        )
        assert len(turn.tool_calls) == 1
        assert len(turn.tool_results) == 1
        assert turn.tool_results[0].content == "file contents"


class TestAgentLoopBasics:
    def test_loop_creation(self):
        """AgentLoop should create without crashing."""
        mock_provider = MagicMock()
        loop = AgentLoop(mock_provider)
        assert loop.max_turns >= 3
        assert not loop.is_cancelled()

    def test_cancel(self):
        """Cancel should set the cancelled flag."""
        mock_provider = MagicMock()
        loop = AgentLoop(mock_provider)
        loop.cancel()
        assert loop.is_cancelled()

    def test_cancelled_loop_yields_error(self):
        """If cancelled before run, should yield error turn immediately."""
        mock_provider = MagicMock()
        loop = AgentLoop(mock_provider)
        loop.cancel()

        session = Session(id="test", title="Test")
        turns = list(loop.run_iter(session))
        assert len(turns) == 1
        assert turns[0].error == "cancelled"

    def test_run_iter_empty_session(self):
        """run_iter with an empty session should make API call."""
        mock_provider = MagicMock()
        mock_provider.stream_sync.return_value = iter(
            [{"type": "content", "text": "Hello!"}]
        )

        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            loop = AgentLoop(mock_provider, max_turns=3)
            session = Session(id="test", title="Test")
            session.add_message(Message(role=Role.USER, content="Hi"))

            turns = list(loop.run_iter(session))
            assert len(turns) == 1
            assert turns[0].content == "Hello!"
            assert not turns[0].error
            mock_provider.stream_sync.assert_called_once()

    def test_run_iter_streaming_callback(self):
        """on_stream callback should be called with accumulated content."""
        mock_provider = MagicMock()
        chunks = [
            {"type": "content", "text": "Hello"},
            {"type": "content", "text": " "},
            {"type": "content", "text": "World!"},
        ]
        mock_provider.stream_sync.return_value = iter(chunks)

        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            loop = AgentLoop(mock_provider, max_turns=3)
            session = Session(id="test", title="Test")
            session.add_message(Message(role=Role.USER, content="Hi"))

            streamed = []
            turns = list(loop.run_iter(session, on_stream=lambda c: streamed.append(c)))
            assert len(turns) == 1
            assert turns[0].content == "Hello World!"
            assert len(streamed) == 3
            assert streamed[-1] == "Hello World!"

    def test_run_iter_with_tool_calls(self):
        """When LLM returns tool calls, they should be yielded in an AgentTurn."""
        mock_provider = MagicMock()

        # First call: tool_call
        # Second call: text response
        call_results = [
            [
                {
                    "type": "tool_call",
                    "id": "c1",
                    "name": "read_file",
                    "arguments": '{"path":"test.txt"}',
                },
            ],
            [
                {"type": "content", "text": "File contents: hello"},
            ],
        ]
        mock_provider.stream_sync.side_effect = [iter(r) for r in call_results]

        # Mock execute_tool to return success
        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            with patch(
                "poplar.core.agent_loop.execute_tool",
                return_value=ToolResult(content="hello"),
            ):
                loop = AgentLoop(mock_provider, max_turns=5)
                session = Session(id="test", title="Test")
                session.add_message(Message(role=Role.USER, content="read test.txt"))

                turns = list(loop.run_iter(session))
                assert len(turns) == 2  # One for tool call, one for final response
                assert len(turns[0].tool_calls) == 1
                assert turns[0].tool_calls[0]["function"]["name"] == "read_file"
                assert len(turns[0].tool_results) == 1
                assert turns[0].tool_results[0].content == "hello"
                assert turns[1].content == "File contents: hello"

    def test_run_iter_retry_on_error(self):
        """Should retry on retryable errors."""
        mock_provider = MagicMock()

        # First call fails, second succeeds
        mock_provider.stream_sync.side_effect = [
            Exception("timeout error"),
            iter([{"type": "content", "text": "Retry worked!"}]),
        ]

        # Mock sleep to avoid waiting
        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            with patch("poplar.core.agent_loop.time.sleep"):
                loop = AgentLoop(mock_provider, max_turns=3)
                session = Session(id="test", title="Test")
                session.add_message(Message(role=Role.USER, content="Hi"))

                turns = list(loop.run_iter(session))
                assert len(turns) == 1
                assert turns[0].content == "Retry worked!"

    def test_run_iter_non_retryable_error(self):
        """Should NOT retry on non-retryable errors (e.g. auth)."""
        mock_provider = MagicMock()
        mock_provider.stream_sync.side_effect = Exception("authentication failed")

        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            with patch("poplar.core.agent_loop.time.sleep"):
                loop = AgentLoop(mock_provider, max_turns=3)
                session = Session(id="test", title="Test")
                session.add_message(Message(role=Role.USER, content="Hi"))

                turns = list(loop.run_iter(session))
                assert len(turns) == 1
                assert turns[0].error is not None
                assert "authentication" in turns[0].error

    def test_run_iter_cancelled_during_stream(self):
        """Cancelling during streaming should yield error turn."""
        mock_provider = MagicMock()

        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            loop = AgentLoop(mock_provider, max_turns=3)

            # Simulate a chunk then cancellation
            def stream_with_cancel(*args, **kwargs):
                yield {"type": "content", "text": "Part1"}
                loop.cancel()
                yield {"type": "content", "text": "Part2"}

            mock_provider.stream_sync.side_effect = stream_with_cancel
            session = Session(id="test", title="Test")
            session.add_message(Message(role=Role.USER, content="Hi"))

            turns = list(loop.run_iter(session))
            assert len(turns) == 1
            assert turns[0].error == "cancelled"

    def test_run_iter_max_turns_exhausted(self):
        """When max_turns is reached with only tool calls, yield fallback."""
        mock_provider = MagicMock()

        # Always return tool calls, never text
        def always_tool(*args, **kwargs):
            yield {
                "type": "tool_call",
                "id": "c1",
                "name": "read_file",
                "arguments": '{"path":"test.txt"}',
            }

        mock_provider.stream_sync.side_effect = always_tool

        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            with patch(
                "poplar.core.agent_loop.execute_tool",
                return_value=ToolResult(content="done"),
            ):
                loop = AgentLoop(mock_provider, max_turns=2)
                session = Session(id="test", title="Test")
                session.add_message(Message(role=Role.USER, content="Hi"))

                turns = list(loop.run_iter(session))
                # Should have 2 tool turns + 1 fallback = 3 turns
                assert len(turns) >= 3
                # Last turn should be the fallback
                assert turns[-1].content is not None
                assert "Tool execution completed" in turns[-1].content

    def test_run_iter_empty_response_error(self):
        """Empty response on first turn should yield error."""
        mock_provider = MagicMock()
        mock_provider.stream_sync.return_value = iter([])  # No chunks

        with patch("poplar.core.agent_loop.get_shared_cache", return_value=None):
            loop = AgentLoop(mock_provider, max_turns=3)
            session = Session(id="test", title="Test")
            session.add_message(Message(role=Role.USER, content="Hi"))

            turns = list(loop.run_iter(session))
            assert len(turns) == 1
            assert turns[0].error == "Empty response from API"


class TestAgentLoopHelpers:
    def test_is_retryable_timeout(self):
        assert AgentLoop._is_retryable("connection timeout") is True

    def test_is_retryable_rate_limit(self):
        assert AgentLoop._is_retryable("rate_limit exceeded") is True

    def test_is_retryable_503(self):
        assert AgentLoop._is_retryable("HTTP 503 Service Unavailable") is True

    def test_is_retryable_not_retryable_auth(self):
        assert AgentLoop._is_retryable("authentication error") is False

    def test_is_retryable_not_retryable_400(self):
        assert AgentLoop._is_retryable("HTTP 400 Bad Request") is False

    def test_is_thinking_msg_true(self):
        msg = Message(role=Role.SYSTEM, content=SPINNER + " thinking... (esc to cancel, 0s)")
        assert is_thinking_message(msg) is True

    def test_is_thinking_msg_not_system(self):
        msg = Message(role=Role.USER, content=SPINNER + " thinking...")
        assert is_thinking_message(msg) is False

    def test_is_thinking_msg_no_spinner(self):
        msg = Message(role=Role.SYSTEM, content="thinking...")
        assert is_thinking_message(msg) is False

    def test_format_tool_calls(self):
        mock_provider = MagicMock()
        loop = AgentLoop(mock_provider)
        raw = [
            {"id": "c1", "name": "read_file", "arguments": '{"path":"test.txt"}'},
        ]
        formatted = loop._format_tool_calls(raw)
        assert len(formatted) == 1
        assert formatted[0]["id"] == "c1"
        assert formatted[0]["type"] == "function"
        assert formatted[0]["function"]["name"] == "read_file"
        assert formatted[0]["function"]["arguments"] == '{"path":"test.txt"}'

    def test_get_api_messages_filters_thinking(self):
        mock_provider = MagicMock()
        loop = AgentLoop(mock_provider)
        session = Session(id="test", title="Test")
        session.add_message(Message(role=Role.SYSTEM, content=SPINNER + " thinking..."))
        session.add_message(Message(role=Role.USER, content="Hello"))
        session.add_message(Message(role=Role.ASSISTANT, content="Hi there"))
        session.add_message(Message(role=Role.SYSTEM, content=SPINNER_CHARS[1] + " thinking... (esc to cancel, 5s)"))

        messages = loop._get_api_messages(session)
        # Should have system prompt + user + assistant = 3 messages
        # The thinking messages are filtered out
        assert len(messages) == 3
        roles = [m.role for m in messages]
        assert roles == [Role.SYSTEM, Role.USER, Role.ASSISTANT]
        assert messages[0].content.startswith("You are Poplar")
