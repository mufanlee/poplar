"""Tests for ollama.py — message formatting, URL construction (no HTTP)."""

from poplar.providers.ollama import OllamaProvider
from poplar.core.session import Message, Role


class TestOllamaProvider:
    def setup_method(self):
        self.provider = OllamaProvider(model="llama3")

    def test_init_defaults(self):
        p = OllamaProvider()
        assert p.base_url == "http://localhost:11434"
        assert p.model == "llama3"

    def test_init_custom(self):
        p = OllamaProvider(
            api_key="sk-test",
            base_url="http://localhost:9999",
            model="codellama",
        )
        assert p.base_url == "http://localhost:9999"
        assert p.model == "codellama"
        assert p.api_key == "sk-test"

    def test_api_url(self):
        assert self.provider._api_url("/api/tags") == "http://localhost:11434/api/tags"
        assert self.provider._api_url("/v1/chat/completions") == "http://localhost:11434/v1/chat/completions"

    def test_headers_no_key(self):
        h = self.provider._headers()
        assert h["Content-Type"] == "application/json"

    def test_headers_with_key(self):
        p = OllamaProvider(api_key="sk-test")
        h = p._headers()
        assert h["Authorization"] == "Bearer sk-test"

    def test_format_messages_empty(self):
        result = self.provider._format_messages([])
        assert result == []

    def test_format_messages(self):
        msgs = [
            Message(role=Role.USER, content="hello"),
            Message(role=Role.ASSISTANT, content="hi"),
        ]
        result = self.provider._format_messages(msgs)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "hello"
        assert result[1]["role"] == "assistant"

    def test_format_messages_with_tool(self):
        msgs = [
            Message(role=Role.TOOL, content="result", tool_call_id="c1", name="read"),
        ]
        result = self.provider._format_messages(msgs)
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "c1"


class TestGetModels:
    def test_fallback_models(self):
        p = OllamaProvider(model="llama3")
        models = p.get_models()
        assert len(models) > 0
        assert models[0].id == "llama3"
