"""Tests for internationalization."""

import os
from poplar.i18n import t, get_language, set_language
from poplar.i18n import DEFAULT_LANGUAGE


def test_default_language():
    assert get_language() == DEFAULT_LANGUAGE


def test_english_translation():
    assert t("thinking") == "Thinking"
    assert t("error") == "Error"
    assert t("welcome_title") == "Poplar"


def test_chinese_translation():
    os.environ["POPLAR_LANGUAGE"] = "zh"
    try:
        assert get_language() == "zh"
        assert t("thinking") == "思考中"
        assert t("error") == "错误"
        assert t("title_you") == "你"
    finally:
        os.environ.pop("POPLAR_LANGUAGE", None)


def test_fallback_to_default():
    result = t("nonexistent_key")
    assert result == "nonexistent_key"


def test_formatted_translation():
    result = t("tool_result_prefix", name="read_file")
    assert "read_file" in result


def test_get_cache_config_defaults():
    """Cache config returns defaults when file has no cache section."""
    from poplar.config import get_cache_config, CACHE_DEFAULTS
    cfg = get_cache_config()
    assert cfg["enabled"] is True
    assert cfg["tool_read_file_ttl"] == 300


def test_get_context_config_defaults():
    """Context config returns defaults when file has no context section."""
    from poplar.config import get_context_config, CONTEXT_DEFAULTS
    cfg = get_context_config()
    assert cfg["max_tokens"] == 32768
    assert cfg["auto_compress_at"] == 0.7


def test_get_provider_config_defaults():
    """Provider config returns deepseek defaults."""
    from poplar.config import get_provider_config, DEFAULT_PROVIDER
    cfg = get_provider_config()
    assert cfg["name"] == DEFAULT_PROVIDER
    assert "model" in cfg["config"]


def test_get_active_provider_name_default():
    from poplar.config import get_active_provider_name, DEFAULT_PROVIDER
    assert get_active_provider_name() == DEFAULT_PROVIDER


def test_set_language_valid(tmp_path, monkeypatch):
    """set_language with valid language should save to config."""
    import poplar.i18n as i18n_mod
    cfg_file = tmp_path / "config.yaml"

    monkeypatch.setattr("poplar.config.get_config_path", lambda: cfg_file)
    # Reset init state
    i18n_mod._language_inited = False
    i18n_mod._current_language = "en"

    assert set_language("zh") is True
    assert i18n_mod._current_language == "zh"


def test_set_language_invalid():
    """set_language with invalid language returns False."""
    assert set_language("jp") is False


def test_t_missing_key_warns(capsys):
    """t() with missing key returns the key itself."""
    result = t("totally_missing_key_xyz")
    assert result == "totally_missing_key_xyz"


def test_init_config_creates_file():
    """Verify init_config creates a file with all expected sections."""
    import tempfile, os, yaml
    from pathlib import Path
    from poplar.config import init_config, get_config_path, load_config
    from poplar.i18n import DEFAULT_LANGUAGE

    tmp_dir = Path(tempfile.mkdtemp())
    import poplar.config as config_mod
    orig = config_mod.get_config_path
    config_mod.get_config_path = lambda: tmp_dir / "config.yaml"
    try:
        cfg = load_config()
        assert "language" in cfg
        assert "provider" in cfg
        assert "cache" in cfg
        assert "context" in cfg
        assert "providers" in cfg
        assert cfg["language"] == "en"
        assert cfg["provider"] == "deepseek"
    finally:
        config_mod.get_config_path = orig
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
