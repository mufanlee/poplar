"""Tests for the context management system."""

import pytest
from poplar.core.context import (
    ContextManager,
    estimate_tokens,
    messages_token_count,
)
from poplar.core.session import Message, Role, Session


class TestTokenEstimation:
    def test_estimate_empty(self):
        assert estimate_tokens("") == 1

    def test_estimate_short(self):
        tokens = estimate_tokens("hello")  # 5 chars → 5//4 = 1
        assert tokens == 1

    def test_estimate_medium(self):
        tokens = estimate_tokens("hello world this is a test")
        # 25 chars / 4 = 6
        assert tokens == 6

    def test_messages_token_count(self):
        msgs = [
            Message(role=Role.USER, content="hello world"),
            Message(role=Role.ASSISTANT, content="hi there"),
        ]
        # 11 + 8 = 19 chars → 19//4 = 4 tokens
        assert messages_token_count(msgs) == 4


class TestContextManager:
    def test_should_compress_below_threshold(self):
        ctx = ContextManager(max_tokens=1000, auto_compress_at=0.7)
        # 700 tokens is threshold, 600 is below
        assert ctx.should_compress(600) is False

    def test_should_compress_at_threshold(self):
        ctx = ContextManager(max_tokens=1000, auto_compress_at=0.7)
        assert ctx.should_compress(700) is True

    def test_should_compress_above_threshold(self):
        ctx = ContextManager(max_tokens=1000, auto_compress_at=0.7)
        assert ctx.should_compress(800) is True

    def test_defaults(self):
        ctx = ContextManager()
        assert ctx.max_tokens == 32768
        assert ctx.auto_compress_at == 0.7
        assert ctx.keep_recent_exchanges == 3

    def test_get_summarizable_messages_empty(self):
        ctx = ContextManager()
        old, recent = ctx.get_summarizable_messages([])
        assert old == []
        assert recent == []

    def test_get_summarizable_messages_few_messages(self):
        """Fewer messages than keep_recent_exchanges → nothing to summarize."""
        ctx = ContextManager(keep_recent_exchanges=3)
        msgs = [
            Message(role=Role.USER, content="hi"),
            Message(role=Role.ASSISTANT, content="hello"),
        ]
        old, recent = ctx.get_summarizable_messages(msgs)
        assert old == []  # Nothing to summarize
        assert recent == msgs

    def test_get_summarizable_messages_splits_correctly(self):
        """More messages than keep_recent → oldest get summarized."""
        ctx = ContextManager(keep_recent_exchanges=2)
        msgs = [
            Message(role=Role.USER, content="msg1"),
            Message(role=Role.ASSISTANT, content="resp1"),
            Message(role=Role.USER, content="msg2"),
            Message(role=Role.ASSISTANT, content="resp2"),
            Message(role=Role.USER, content="msg3"),
            Message(role=Role.ASSISTANT, content="resp3"),
        ]
        old, recent = ctx.get_summarizable_messages(msgs)
        # Should keep last 2 exchanges (msg2+resp2, msg3+resp3)
        assert len(old) == 2  # msg1 + resp1
        assert len(recent) == 4  # msg2 + resp2 + msg3 + resp3
        assert old[0].content == "msg1"
        assert recent[0].content == "msg2"

    def test_get_summarizable_skips_existing_summaries(self):
        """Messages that are already summaries should not be re-summarized."""
        ctx = ContextManager(keep_recent_exchanges=1)
        msgs = [
            Message(role=Role.SYSTEM, content="[Summary of earlier conversation]\n..."),
            Message(role=Role.USER, content="msg1"),
            Message(role=Role.ASSISTANT, content="resp1"),
            Message(role=Role.USER, content="msg2"),
            Message(role=Role.ASSISTANT, content="resp2"),
        ]
        old, recent = ctx.get_summarizable_messages(msgs)
        # The summary SYSTEM message should be excluded from old_msgs
        # old should be [msg1, resp1] (the summary itself filtered out)
        assert len(old) == 2
        assert all(m.content != "[Summary of earlier conversation]\n..." for m in old)

    def test_build_summary_prompt(self):
        ctx = ContextManager()
        msgs = [
            Message(role=Role.USER, content="hello"),
            Message(role=Role.ASSISTANT, content="world"),
        ]
        prompt = ctx.build_summary_prompt(msgs)
        assert "hello" in prompt
        assert "world" in prompt
        assert "user" in prompt or "[user]" in prompt

    def test_format_summary_message(self):
        msg = ContextManager.format_summary_message("test summary")
        assert msg.role == Role.SYSTEM
        assert "[Summary of earlier conversation]" in msg.content
        assert "test summary" in msg.content

    def test_apply_compression(self):
        ctx = ContextManager()
        session = Session(id="test", title="Test")
        session.messages = [
            Message(role=Role.USER, content="old1"),
            Message(role=Role.ASSISTANT, content="old_resp1"),
            Message(role=Role.USER, content="new1"),
            Message(role=Role.ASSISTANT, content="new_resp1"),
        ]
        recent = [
            Message(role=Role.USER, content="new1"),
            Message(role=Role.ASSISTANT, content="new_resp1"),
        ]
        ctx.apply_compression(session, "Summary text", recent)
        assert len(session.messages) == 3  # summary + 2 recent
        assert session.messages[0].role == Role.SYSTEM
        assert "[Summary" in session.messages[0].content
        assert session.messages[1].content == "new1"

    def test_get_cumulative_token_count(self):
        session = Session(id="test", title="Test")
        session.messages = [
            Message(role=Role.USER, content="hello world"),
            Message(role=Role.ASSISTANT, content="hi there"),
        ]
        count = ContextManager.get_cumulative_token_count(session)
        # 11 + 8 = 19 chars → 4 tokens
        assert count == 4

    def test_get_cumulative_token_count_with_summary(self):
        """Summary messages should be counted (they contain conversation context)."""
        session = Session(id="test", title="Test")
        session.messages = [
            Message(role=Role.SYSTEM, content="[Summary of earlier conversation]\nimportant context"),
            Message(role=Role.USER, content="new question"),
        ]
        count = ContextManager.get_cumulative_token_count(session)
        # Summary + user message both counted
        assert count > 2

    def test_summarize_calls_function(self):
        ctx = ContextManager()
        msgs = [Message(role=Role.USER, content="hello")]
        called = [False]
        def fake_summarizer(prompt: str) -> str:
            called[0] = True
            return "fake summary"
        result = ctx.summarize(fake_summarizer, msgs)
        assert called[0] is True
        assert result == "fake summary"
