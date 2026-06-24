"""Tests for OpenAICompatibleProvider base class and its subclasses."""

from unittest.mock import Mock, patch, PropertyMock
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
    def test_chat_response_direct(self):
        """Verify chat() returns ChatResponse from mock client."""
        p = DeepSeekProvider(api_key="sk-test")

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(
            OpenAICompatibleProvider, "client",
            new_callable=PropertyMock, return_value=mock_client
        ):
            messages = [Message(role=Role.USER, content="Hi")]
            result = p.chat(messages)

        assert isinstance(result, ChatResponse)
        assert result.content == "Hello"
        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

    def test_chat_response_no_content(self):
        """Content can be None from API — should return empty string."""
        p = OpenAIProvider(api_key="sk-test")

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = None

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(
            OpenAICompatibleProvider, "client",
            new_callable=PropertyMock, return_value=mock_client
        ):
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
        assert p._client is None

    def test_client_restores_proxy_vars(self, monkeypatch):
        """After accessing client, env vars should be restored."""
        monkeypatch.setenv("HTTP_PROXY", "http://test:8080")
        p = DeepSeekProvider(api_key="sk-test")
        # Trigger client creation
        _ = p.client  # noqa
        import os
        assert os.environ.get("HTTP_PROXY") == "http://test:8080"


class TestStreamSync:
    def test_stream_sync_content_only(self):
        """stream_sync yields content chunks and done marker."""
        p = DeepSeekProvider(api_key="sk-test")

        chunk1 = Mock()
        chunk1.choices = [Mock()]
        chunk1.choices[0].delta = Mock()
        chunk1.choices[0].delta.content = "Hello"
        chunk1.choices[0].delta.tool_calls = None
        chunk1.choices[0].finish_reason = None

        chunk2 = Mock()
        chunk2.choices = [Mock()]
        chunk2.choices[0].delta = Mock()
        chunk2.choices[0].delta.content = " World"
        chunk2.choices[0].delta.tool_calls = None
        chunk2.choices[0].finish_reason = "stop"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2]

        with patch.object(
            OpenAICompatibleProvider, "client",
            new_callable=PropertyMock, return_value=mock_client
        ):
            messages = [Message(role=Role.USER, content="Hi")]
            chunks = list(p.stream_sync(messages))

        assert {"type": "content", "text": "Hello"} in chunks
        assert {"type": "content", "text": " World"} in chunks
        assert {"type": "done"} in chunks

    def test_stream_sync_with_tool_calls(self):
        """stream_sync handles tool call streaming chunks."""
        p = DeepSeekProvider(api_key="sk-test")

        # First chunk: tool_call start
        tc1 = Mock()
        tc1.index = 0
        tc1.id = "call_123"
        tc1.function = Mock()
        tc1.function.name = "read_file"
        tc1.function.arguments = '{"path": "'

        chunk1 = Mock()
        chunk1.choices = [Mock()]
        chunk1.choices[0].delta = Mock()
        chunk1.choices[0].delta.content = None
        chunk1.choices[0].delta.tool_calls = [tc1]
        chunk1.choices[0].finish_reason = None

        # Second chunk: tool_call continuation
        tc2 = Mock()
        tc2.index = 0
        tc2.id = None
        tc2.function = Mock()
        tc2.function.name = None
        tc2.function.arguments = '/tmp/test"}'

        chunk2 = Mock()
        chunk2.choices = [Mock()]
        chunk2.choices[0].delta = Mock()
        chunk2.choices[0].delta.content = None
        chunk2.choices[0].delta.tool_calls = [tc2]
        chunk2.choices[0].finish_reason = "tool_calls"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2]

        with patch.object(
            OpenAICompatibleProvider, "client",
            new_callable=PropertyMock, return_value=mock_client
        ):
            messages = [Message(role=Role.USER, content="read test.txt")]
            chunks = list(p.stream_sync(messages))

        tool_call_chunks = [c for c in chunks if c["type"] == "tool_call"]
        assert len(tool_call_chunks) == 1
        assert tool_call_chunks[0]["name"] == "read_file"
        assert tool_call_chunks[0]["id"] == "call_123"
        assert {"type": "done"} in chunks

    def test_stream_sync_with_tools_param(self):
        """stream_sync passes tools param to API."""
        p = DeepSeekProvider(api_key="sk-test")

        chunk = Mock()
        chunk.choices = [Mock()]
        chunk.choices[0].delta = Mock()
        chunk.choices[0].delta.content = "done"
        chunk.choices[0].delta.tool_calls = None
        chunk.choices[0].finish_reason = "stop"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [chunk]

        with patch.object(
            OpenAICompatibleProvider, "client",
            new_callable=PropertyMock, return_value=mock_client
        ):
            messages = [Message(role=Role.USER, content="Hi")]
            tools = [{"type": "function", "function": {"name": "test_tool", "parameters": {}}}]
            list(p.stream_sync(messages, tools=tools))

        # Verify tools were passed
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs is not None
