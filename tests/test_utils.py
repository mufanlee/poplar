"""Tests for utils.py — shared utilities."""

from pathlib import Path
from poplar.utils import get_writable_dir, get_db_path, is_thinking_message, SPINNER_CHARS
from poplar.core.session import Message, Role


class TestSpinnerChars:
    def test_not_empty(self):
        assert len(SPINNER_CHARS) > 0

    def test_all_braille(self):
        for c in SPINNER_CHARS:
            assert ord(c) in range(0x2800, 0x2900)


class TestIsThinkingMessage:
    def test_system_with_spinner_is_thinking(self):
        m = Message(role=Role.SYSTEM, content="⠋ Thinking... (esc to cancel, 0s)")
        assert is_thinking_message(m) is True

    def test_system_without_spinner_is_not_thinking(self):
        m = Message(role=Role.SYSTEM, content="System notification")
        assert is_thinking_message(m) is False

    def test_user_message_is_not_thinking(self):
        m = Message(role=Role.USER, content="⠋ hello")
        assert is_thinking_message(m) is False

    def test_assistant_message_is_not_thinking(self):
        m = Message(role=Role.ASSISTANT, content="⠋ I'm thinking")
        assert is_thinking_message(m) is False

    def test_tool_message_is_not_thinking(self):
        m = Message(role=Role.TOOL, content="⠋ result")
        assert is_thinking_message(m) is False

    def test_empty_content(self):
        m = Message(role=Role.SYSTEM, content="")
        assert is_thinking_message(m) is False

    def test_none_content(self):
        m = Message(role=Role.SYSTEM, content="")  # content is str not None
        m.content = ""  # re-set empty
        assert is_thinking_message(m) is False


class TestGetWritableDir:
    def test_returns_path(self):
        d = get_writable_dir()
        assert isinstance(d, Path)
        assert d.is_dir()

    def test_with_subdir(self):
        d = get_writable_dir("test_sub")
        assert d.name == "test_sub"
        assert d.exists()

    def test_is_writable(self):
        d = get_writable_dir()
        test_file = d / ".write_test"
        test_file.touch()
        assert test_file.exists()
        test_file.unlink()


class TestGetDbPath:
    def test_returns_string(self):
        p = get_db_path()
        assert isinstance(p, str)
        assert p.endswith("poplar.db")

    def test_in_poplar_dir(self):
        p = get_db_path()
        assert ".poplar" in p
