"""Tests for SQLite persistence layer."""

import tempfile
import os
from poplar.persistence.store import SessionStore
from poplar.core.session import Message, Role


def test_create_session():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        session = store.create_session(title="Test")
        assert session.title == "Test"
        assert session.id is not None
        assert len(session.messages) == 0


def test_list_sessions():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        store.create_session(title="A")
        store.create_session(title="B")
        sessions = store.list_sessions()
        assert len(sessions) == 2


def test_save_and_load_messages():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        s = store.create_session(title="Chat")
        store.save_message(s.id, Message(role=Role.USER, content="hello"))
        store.save_message(s.id, Message(role=Role.ASSISTANT, content="hi there"))

        loaded = store.get_session(s.id)
        assert len(loaded.messages) == 2
        assert loaded.messages[0].role == Role.USER
        assert loaded.messages[0].content == "hello"
        assert loaded.messages[1].role == Role.ASSISTANT


def test_save_tool_message():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        s = store.create_session(title="Chat")
        tool_msg = Message(role=Role.TOOL, content="result", tool_call_id="call_1", name="read_file")
        store.save_message(s.id, tool_msg)

        loaded = store.get_session(s.id)
        assert len(loaded.messages) == 1
        assert loaded.messages[0].role == Role.TOOL
        assert loaded.messages[0].tool_call_id == "call_1"
        assert loaded.messages[0].name == "read_file"


def test_save_assistant_with_tool_calls():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        s = store.create_session(title="Chat")
        msg = Message(role=Role.ASSISTANT, content=None, tool_calls=[
            {"id": "c1", "type": "function", "function": {"name": "f", "arguments": "{}"}}
        ])
        store.save_message(s.id, msg)

        loaded = store.get_session(s.id)
        assert loaded.messages[0].tool_calls is not None
        assert loaded.messages[0].tool_calls[0]["function"]["name"] == "f"


def test_delete_session():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        s = store.create_session(title="To Delete")
        store.save_message(s.id, Message(role=Role.USER, content="hi"))
        store.delete_session(s.id)
        assert store.get_session(s.id) is None
        assert len(store.list_sessions()) == 0


def test_update_title():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        s = store.create_session(title="Old")
        store.update_title(s.id, "New")
        loaded = store.get_session(s.id)
        assert loaded.title == "New"


def test_get_nonexistent_session():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        assert store.get_session("nonexistent") is None


def test_message_count():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        s = store.create_session(title="Chat")
        store.save_message(s.id, Message(role=Role.USER, content="hi"))
        store.save_message(s.id, Message(role=Role.SYSTEM, content="thinking"))
        count = store.get_message_count(s.id)
        assert count == 1  # excludes system messages


def test_auto_create_default_session():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = SessionStore(db)
        s = store.create_session(title="New Chat")
        assert s.id is not None
        assert store.get_session(s.id) is not None
