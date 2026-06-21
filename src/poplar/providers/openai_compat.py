"""Base class for OpenAI-compatible providers (OpenAI, DeepSeek, etc.)."""

import os
import openai
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any
from poplar.providers.base import ChatResponse, ModelInfo
from poplar.core.session import Message


class OpenAICompatibleProvider:
    """Shared logic for any provider using the OpenAI SDK/API format.

    Subclasses only need to set _DEFAULT_BASE_URL, _DEFAULT_MODEL,
    and override get_models().
    """

    _DEFAULT_BASE_URL: str = "https://api.openai.com/v1"
    _DEFAULT_MODEL: str = "gpt-4o"

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or self._DEFAULT_BASE_URL
        self.model = model or self._DEFAULT_MODEL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            saved = {}
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
                saved[var] = os.environ.pop(var, None)
            try:
                self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            finally:
                for var, val in saved.items():
                    if val is not None:
                        os.environ[var] = val
        return self._client

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        api_messages = [msg.to_dict() for msg in messages]
        response = self.client.chat.completions.create(
            model=self.model, messages=api_messages, **kwargs  # type: ignore[arg-type]
        )
        content = response.choices[0].message.content or ""
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return ChatResponse(content=content, usage=usage)

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        api_messages = [msg.to_dict() for msg in messages]
        stream = self.client.chat.completions.create(
            model=self.model, messages=api_messages, stream=True, **kwargs  # type: ignore[arg-type]
        )
        for chunk in stream:  # type: ignore[union-attr]
            if chunk.choices[0].delta.content:  # type: ignore[union-attr]
                yield chunk.choices[0].delta.content  # type: ignore[union-attr]

    def stream_sync(self, messages: List[Message], tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Iterator[Dict[str, Any]]:
        """Stream with optional tool calling support."""
        api_messages = [msg.to_dict() for msg in messages]
        params: dict = dict(model=self.model, messages=api_messages, stream=True, **kwargs)
        if tools:
            params["tools"] = tools

        stream = self.client.chat.completions.create(**params)  # type: ignore[arg-type]
        tool_calls: Dict[int, Dict] = {}

        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                    if tc.function and tc.function.name:
                        tool_calls[idx]["name"] += tc.function.name
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function and tc.function.arguments:
                        tool_calls[idx]["arguments"] += tc.function.arguments

            if delta.content:
                yield {"type": "content", "text": delta.content}

            if chunk.choices[0].finish_reason == "tool_calls":
                for tc in tool_calls.values():
                    yield {"type": "tool_call", **tc}

        yield {"type": "done"}

    def get_models(self) -> List[ModelInfo]:
        raise NotImplementedError("Subclasses must override get_models()")
