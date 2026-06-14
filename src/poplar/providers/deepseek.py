import os
import json
import openai
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any
from poplar.providers.base import Provider, ChatResponse, ModelInfo
from poplar.core.session import Message


class DeepSeekProvider:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key: str = api_key
        self.base_url: str = base_url
        self.model: str = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        api_messages = [msg.to_dict() for msg in messages]
        response = self.client.chat.completions.create(
            model=self.model, messages=api_messages, **kwargs  # type: ignore[arg-type]
        )
        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
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

            # Handle tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls[idx]["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls[idx]["arguments"] += tc.function.arguments

            # Handle content
            if delta.content:
                yield {"type": "content", "text": delta.content}

            # Check finish reason
            if chunk.choices[0].finish_reason == "tool_calls":
                for tc in tool_calls.values():
                    yield {"type": "tool_call", **tc}

        yield {"type": "done"}

    def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat"),
            ModelInfo(id="deepseek-coder", name="DeepSeek Coder"),
        ]
