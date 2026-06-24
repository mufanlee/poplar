"""Tests for providers/base.py — ChatResponse, ModelInfo dataclasses."""

from poplar.providers.base import ChatResponse, ModelInfo


class TestChatResponse:
    def test_defaults(self):
        r = ChatResponse("hello")
        assert r.content == "hello"
        assert r.usage == {}

    def test_with_usage(self):
        r = ChatResponse("hi", usage={"prompt_tokens": 10, "completion_tokens": 5})
        assert r.content == "hi"
        assert r.usage["prompt_tokens"] == 10
        assert r.usage["completion_tokens"] == 5

    def test_empty_content(self):
        r = ChatResponse("")
        assert r.content == ""

    def test_content_is_string(self):
        r = ChatResponse("test")
        assert isinstance(r.content, str)

    def test_usage_is_dict(self):
        r = ChatResponse("x")
        assert isinstance(r.usage, dict)


class TestModelInfo:
    def test_create(self):
        m = ModelInfo(id="gpt-4", name="GPT-4")
        assert m.id == "gpt-4"
        assert m.name == "GPT-4"

    def test_equality(self):
        m1 = ModelInfo(id="x", name="X")
        m2 = ModelInfo(id="x", name="X")
        assert m1.id == m2.id
        assert m1.name == m2.name
