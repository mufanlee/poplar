"""Tests for config.py — defaults, provider/cache/context config, persist."""

import yaml
from poplar.config import (
    DEFAULT_LANGUAGE,
    DEFAULT_PROVIDER,
    CACHE_DEFAULTS,
    CONTEXT_DEFAULTS,
    PROVIDER_DEFAULTS,
    get_cache_config,
    get_context_config,
    get_provider_config,
    get_active_provider_name,
    get_config_path,
    save_config,
    load_config,
    init_config,
)


class TestDefaults:
    def test_default_language(self):
        assert DEFAULT_LANGUAGE == "en"

    def test_default_provider(self):
        assert DEFAULT_PROVIDER == "deepseek"

    def test_cache_defaults_structure(self):
        assert CACHE_DEFAULTS["enabled"] is True
        assert CACHE_DEFAULTS["max_memory_items"] == 100
        assert "tool_read_file_ttl" in CACHE_DEFAULTS
        assert "tool_list_dir_ttl" in CACHE_DEFAULTS
        assert "api_response_ttl" in CACHE_DEFAULTS

    def test_context_defaults_structure(self):
        assert CONTEXT_DEFAULTS["max_turns"] == 100
        assert CONTEXT_DEFAULTS["max_tokens"] == 32768
        assert "auto_compress_at" in CONTEXT_DEFAULTS
        assert "keep_recent_exchanges" in CONTEXT_DEFAULTS

    def test_provider_defaults_has_core_providers(self):
        assert "deepseek" in PROVIDER_DEFAULTS
        assert "openai" in PROVIDER_DEFAULTS
        assert "anthropic" in PROVIDER_DEFAULTS
        assert "ollama" in PROVIDER_DEFAULTS

    def test_deepseek_defaults(self):
        assert PROVIDER_DEFAULTS["deepseek"]["model"] == "deepseek-chat"

    def test_openai_defaults(self):
        assert PROVIDER_DEFAULTS["openai"]["model"] == "gpt-4o"

    def test_ollama_defaults(self):
        assert PROVIDER_DEFAULTS["ollama"]["model"] == "llama3"
        assert "base_url" in PROVIDER_DEFAULTS["ollama"]


class TestConfigMerge:
    """Test that config functions merge user overrides with defaults."""

    def test_get_cache_config_returns_dict(self):
        cfg = get_cache_config()
        assert isinstance(cfg, dict)
        assert cfg["enabled"] is True  # default

    def test_get_context_config_returns_dict(self):
        cfg = get_context_config()
        assert isinstance(cfg, dict)
        assert cfg["max_turns"] == 100  # updated default

    def test_get_active_provider_name(self):
        name = get_active_provider_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_provider_config_returns_name_and_config(self):
        cfg = get_provider_config()
        assert "name" in cfg
        assert "config" in cfg
        assert "model" in cfg["config"]


class TestConfigIO:
    """Test save/load using real filesystem (tmp_path)."""

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.yaml"
        monkeypatch.setattr(
            "poplar.config.get_config_path",
            lambda: cfg_file,
        )
        saved = {"language": "zh", "provider": "openai"}
        save_config(saved)
        assert cfg_file.exists()
        loaded = load_config()
        assert loaded["language"] == "zh"
        assert loaded["provider"] == "openai"

    def test_init_config_creates_file(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "new_config.yaml"
        monkeypatch.setattr(
            "poplar.config.get_config_path",
            lambda: cfg_file,
        )
        assert not cfg_file.exists()
        init_config()
        assert cfg_file.exists()
        loaded = load_config()
        assert "language" in loaded
        assert "provider" in loaded

    def test_load_config_empty_file(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "empty.yaml"
        cfg_file.write_text("")
        monkeypatch.setattr(
            "poplar.config.get_config_path",
            lambda: cfg_file,
        )
        loaded = load_config()
        assert loaded == {}

    def test_save_config_creates_parent_dir(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "sub" / "deep" / "config.yaml"
        monkeypatch.setattr(
            "poplar.config.get_config_path",
            lambda: cfg_file,
        )
        save_config({"provider": "deepseek"})
        assert cfg_file.exists()

    def test_get_config_path_returns_correct_path(self):
        path = get_config_path()
        assert path.name == "config.yaml"
        assert ".poplar" in str(path)
