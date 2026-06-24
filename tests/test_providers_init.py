"""Tests for providers/__init__.py — registry and factory."""

import pytest
from poplar.providers import create_provider, get_available_providers


class TestCreateProvider:
    def test_create_ollama_no_api_key_needed(self):
        p = create_provider("ollama")
        assert p.model == "llama3"

    def test_create_ollama_with_custom_url(self):
        p = create_provider("ollama", {"base_url": "http://localhost:8080"})
        assert p.base_url == "http://localhost:8080"

    def test_create_ollama_with_custom_model(self):
        p = create_provider("ollama", {"model": "codellama"})
        assert p.model == "codellama"

    def test_create_deepseek_with_key(self):
        p = create_provider("deepseek", {"api_key": "sk-test"})
        assert p.model == "deepseek-chat"

    def test_create_openai_with_key(self):
        p = create_provider("openai", {"api_key": "sk-test"})
        assert p.model == "gpt-4o"

    def test_create_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("nonexistent")

    def test_create_deepseek_custom_model(self):
        p = create_provider("deepseek", {"api_key": "sk-test", "model": "deepseek-v4-flash"})
        assert p.model == "deepseek-v4-flash"


class TestGetAvailableProviders:
    def test_returns_list(self):
        providers = get_available_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

    def test_includes_all_registered(self):
        providers = get_available_providers()
        assert "deepseek" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_count_is_4(self):
        assert len(get_available_providers()) == 4
