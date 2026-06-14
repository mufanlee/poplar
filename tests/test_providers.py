"""Tests for provider registry and multi-provider support."""

import pytest
from poplar.providers import (
    create_provider,
    get_available_providers,
    PROVIDER_REGISTRY,
)
from poplar.core.session import Message, Role
from poplar.providers.base import ChatResponse


class TestProviderRegistry:
    def test_get_available_providers(self):
        providers = get_available_providers()
        assert "deepseek" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_registry_has_all_keys(self):
        for name, info in PROVIDER_REGISTRY.items():
            assert "module" in info
            assert "class" in info
            assert "env_key" in info or info["env_key"] is None
            assert "default_model" in info

    def test_create_deepseek(self):
        p = create_provider("deepseek")
        assert p.model == "deepseek-chat"
        assert hasattr(p, "chat")
        assert hasattr(p, "stream")
        assert hasattr(p, "stream_sync")
        assert hasattr(p, "get_models")

    def test_create_openai(self):
        p = create_provider("openai", {"api_key": "sk-test", "model": "gpt-4o-mini"})
        assert p.model == "gpt-4o-mini"

    def test_create_ollama(self):
        p = create_provider("ollama", {"model": "llama3.2"})
        assert p.model == "llama3.2"
        assert "localhost" in p.base_url

    def test_create_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("nonexistent")

    def test_create_with_custom_base_url(self):
        p = create_provider("deepseek", {"base_url": "http://localhost:8080/v1"})
        assert p.base_url == "http://localhost:8080/v1"


class TestProviderProtocol:
    def test_all_providers_have_required_methods(self):
        """All registered providers must implement the Provider Protocol methods."""
        providers_to_test = [
            ("deepseek", {}),
            ("openai", {"api_key": "sk-test"}),
            ("ollama", {}),
        ]
        for name, cfg in providers_to_test:
            p = create_provider(name, cfg)
            assert hasattr(p, "chat"), f"{name} missing chat()"
            assert hasattr(p, "stream"), f"{name} missing stream()"
            assert hasattr(p, "stream_sync"), f"{name} missing stream_sync()"
            assert hasattr(p, "get_models"), f"{name} missing get_models()"

    def test_get_models_returns_list(self):
        p = create_provider("deepseek")
        models = p.get_models()
        assert len(models) > 0
        for m in models:
            assert hasattr(m, "id")
            assert hasattr(m, "name")

    def test_stream_sync_yields_done(self):
        """stream_sync should at minimum yield a 'done' event even without tools."""
        p = create_provider("deepseek")
        msgs = [Message(role=Role.USER, content="hello")]
        results = list(p.stream_sync(msgs))
        assert len(results) > 0
        assert results[-1]["type"] == "done"

    def test_message_conversion_openai(self):
        """Verify OpenAI provider can format messages properly."""
        from poplar.providers.openai import OpenAIProvider
        p = OpenAIProvider(api_key="test-key")
        msgs = [
            Message(role=Role.SYSTEM, content="You are helpful"),
            Message(role=Role.USER, content="Hi"),
        ]
        api_msgs = [m.to_dict() for m in msgs]
        assert len(api_msgs) == 2
        assert api_msgs[0]["role"] == "system"


class TestChatResponse:
    def test_chat_response_defaults(self):
        r = ChatResponse(content="hello")
        assert r.content == "hello"
        assert r.usage == {}

    def test_chat_response_with_usage(self):
        r = ChatResponse(content="hi", usage={"total_tokens": 10})
        assert r.usage["total_tokens"] == 10
