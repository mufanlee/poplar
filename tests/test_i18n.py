"""Tests for internationalization."""

import os
from poplar.i18n import t, get_language, set_language, DEFAULT_LANGUAGE


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
