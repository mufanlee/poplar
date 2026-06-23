"""Tests for _merge_tool_content in PoplarApp."""
import pytest
from poplar.core.session import Message, Role, Session


class FakeStore:
    def save_message(self, *args):
        pass


class FakeApp:
    def __init__(self, messages):
        self.session = Session(id="test", title="Test")
        self.session.messages = list(messages)
        self.store = FakeStore()

    def _merge_tool_content(self, final):
        from poplar.tui.app import PoplarApp
        return PoplarApp._merge_tool_content(self, final)


def _a(content, tool_calls=None):
    return Message(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)

def _t(content, name="list_directory", tc_id="c1"):
    return Message(role=Role.TOOL, content=content, name=name, tool_call_id=tc_id)

def _u(content):
    return Message(role=Role.USER, content=content)


class TestMergeToolContent:
    def test_no_tools_normal(self):
        app = FakeApp([_u("hi"), _a("Hello!"), _u("how are you")])
        merged, did_merge = app._merge_tool_content("I am fine")
        assert did_merge is False
        assert merged == "I am fine"
        assert len(app.session.messages) == 3

    def test_with_tools_merges_and_cleans(self):
        app = FakeApp([
            _u("list files"),
            _a("Let me check", tool_calls=[{"id": "c1", "type": "function", "function": {"name": "list_directory", "arguments": "{}"}}]),
            _t("src/\ntests/"),
        ])
        merged, did_merge = app._merge_tool_content("Found 2 dirs")
        assert did_merge is True
        assert "Let me check" in merged
        assert "🔧 list_directory" in merged
        assert "src/" in merged
        assert "Found 2 dirs" in merged
        assert len(app.session.messages) == 2
        assert app.session.messages[1].tool_calls is None

    def test_multiple_tools(self):
        app = FakeApp([
            _u("do stuff"),
            _a("Checking...", tool_calls=[{"id": "c1", "type": "function", "function": {"name": "f1", "arguments": "{}"}}]),
            _t("r1", name="read_file", tc_id="c1"),
            _t("r2", name="list_directory", tc_id="c2"),
        ])
        merged, did_merge = app._merge_tool_content("All done")
        assert did_merge is True
        assert "🔧 read_file" in merged
        assert "🔧 list_directory" in merged
        assert "All done" in merged
        assert len(app.session.messages) == 2

    def test_no_tool_chain_no_merge(self):
        app = FakeApp([_u("hi"), _a("Hello!"), _u("what?")])
        merged, did_merge = app._merge_tool_content("Response")
        assert did_merge is False
        assert len(app.session.messages) == 3

    def test_empty_assistant_content(self):
        app = FakeApp([
            _u("do it"),
            _a("", tool_calls=[{"id": "c1", "type": "function", "function": {"name": "list_directory", "arguments": "{}"}}]),
            _t("result"),
        ])
        merged, did_merge = app._merge_tool_content("Done")
        assert did_merge is True
        # Empty prefix should not add leading blank
        assert not merged.startswith("\n")
