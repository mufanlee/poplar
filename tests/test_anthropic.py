"""Tests for anthropic.py — message conversion (no API calls needed)."""

from poplar.providers.anthropic import AnthropicProvider
from poplar.core.session import Message, Role


class TestConvertMessages:
    """Tests for _convert_messages which doesn't require API calls."""

    def setup_method(self):
        self.provider = AnthropicProvider(api_key="test-key")

    def test_simple_user_message(self):
        msgs = [Message(role=Role.USER, content="hello")]
        system, anthro = self.provider._convert_messages(msgs)
        assert system is None
        assert len(anthro) == 1
        assert anthro[0]["role"] == "user"
        assert anthro[0]["content"] == "hello"

    def test_assistant_message_maps_to_assistant(self):
        msgs = [Message(role=Role.ASSISTANT, content="hi there")]
        system, anthro = self.provider._convert_messages(msgs)
        assert anthro[0]["role"] == "assistant"
        assert anthro[0]["content"] == "hi there"

    def test_tool_message_maps_to_user(self):
        msgs = [Message(role=Role.TOOL, content="result", tool_call_id="c1", name="read")]
        system, anthro = self.provider._convert_messages(msgs)
        assert anthro[0]["role"] == "user"
        assert "result" in anthro[0]["content"]

    def test_system_message_becomes_system_prompt(self):
        msgs = [Message(role=Role.SYSTEM, content="You are helpful")]
        system, anthro = self.provider._convert_messages(msgs)
        assert system == "You are helpful"
        assert len(anthro) == 0

    def test_multiple_system_messages_concatenated(self):
        msgs = [
            Message(role=Role.SYSTEM, content="Rule 1"),
            Message(role=Role.SYSTEM, content="Rule 2"),
        ]
        system, anthro = self.provider._convert_messages(msgs)
        assert "Rule 1" in system
        assert "Rule 2" in system

    def test_mixed_messages(self):
        msgs = [
            Message(role=Role.SYSTEM, content="Be helpful"),
            Message(role=Role.USER, content="question"),
            Message(role=Role.ASSISTANT, content="answer"),
        ]
        system, anthro = self.provider._convert_messages(msgs)
        assert system == "Be helpful"
        assert len(anthro) == 2
        assert anthro[0]["role"] == "user"
        assert anthro[1]["role"] == "assistant"

    def test_empty_messages(self):
        system, anthro = self.provider._convert_messages([])
        assert system is None
        assert anthro == []


class TestGetModels:
    def test_returns_list(self):
        provider = AnthropicProvider(api_key="test-key")
        models = provider.get_models()
        assert len(models) > 0
        assert all(m.id and m.name for m in models)

    def test_has_sonnet(self):
        provider = AnthropicProvider(api_key="test-key")
        models = provider.get_models()
        ids = [m.id for m in models]
        assert "claude-3-5-sonnet-20241022" in ids
