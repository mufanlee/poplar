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
