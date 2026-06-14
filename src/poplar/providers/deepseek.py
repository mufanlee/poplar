import os
import json
import openai
from typing import List, AsyncIterator, Iterator, Dict, Any
from poplar.providers.base import Provider, ChatResponse, ModelInfo
from poplar.core.session import Message


class DeepSeekProvider:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
            os.environ.pop(var, None)

        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        api_messages = [msg.to_dict() for msg in messages]
        response = self.client.chat.completions.create(
            model=self.model, messages=api_messages, **kwargs
        )
        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        return ChatResponse(content=content, usage=usage)

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        api_messages = [msg.to_dict() for msg in messages]
        stream = self.client.chat.completions.create(
            model=self.model, messages=api_messages, stream=True, **kwargs
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def stream_sync(self, messages: List[Message], tools: List[Dict] = None, **kwargs) -> Iterator[Dict[str, Any]]:
        """Stream with optional tool calling support.
        
        Yields dicts:
        - {"type": "content", "text": "..."}
        - {"type": "tool_call", "id": "...", "name": "...", "arguments": "..."}
        - {"type": "done"}
        """
        api_messages = [msg.to_dict() for msg in messages]
        params = dict(model=self.model, messages=api_messages, stream=True, **kwargs)
        if tools:
            params["tools"] = tools

        stream = self.client.chat.completions.create(**params)
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
