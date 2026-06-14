"""Anthropic provider — uses the anthropic SDK for Claude models."""

import json
import os
from typing import List, AsyncIterator, Iterator, Dict, Any
from poplar.providers.base import ChatResponse, ModelInfo
from poplar.core.session import Message


class AnthropicProvider:
    """Provider for Anthropic Claude models."""

    def __init__(self, api_key: str, base_url: str = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
            os.environ.pop(var, None)

    def _client(self):
        import anthropic
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return anthropic.Anthropic(**kwargs)

    def _convert_messages(self, messages: List[Message]) -> tuple:
        """Convert internal Message list to Anthropic format.

        Returns (system_prompt, anthropic_messages).
        """
        system = None
        anthro_msgs = []

        for m in messages:
            if m.role.value == "system":
                system = (system or "") + m.content + "\n"
                continue
            role = "assistant" if m.role.value == "assistant" else "user"
            anthro_msgs.append({"role": role, "content": m.content})

        return system.strip() if system else None, anthro_msgs

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        client = self._client()
        system, anthro_msgs = self._convert_messages(messages)

        create_kwargs = dict(model=self.model, messages=anthro_msgs, max_tokens=4096, **kwargs)
        if system:
            create_kwargs["system"] = system

        response = client.messages.create(**create_kwargs)
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0),
            }
        return ChatResponse(content=content, usage=usage)

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.api_key)
        system, anthro_msgs = self._convert_messages(messages)

        create_kwargs = dict(model=self.model, messages=anthro_msgs, max_tokens=4096, stream=True, **kwargs)
        if system:
            create_kwargs["system"] = system

        async with client.messages.stream(**create_kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    def stream_sync(self, messages: List[Message], tools: List[Dict] = None, **kwargs) -> Iterator[Dict[str, Any]]:
        """Stream with optional tool calling support."""
        client = self._client()
        system, anthro_msgs = self._convert_messages(messages)

        create_kwargs = dict(model=self.model, messages=anthro_msgs, max_tokens=4096, stream=True, **kwargs)
        if system:
            create_kwargs["system"] = system

        # Convert OpenAI-style tool definitions to Anthropic format
        if tools:
            anthro_tools = []
            for t in tools:
                fn = t.get("function", t)
                anthro_tools.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {}),
                })
            create_kwargs["tools"] = anthro_tools

        with client.messages.stream(**create_kwargs) as stream:
            for text_delta in stream.text_stream:
                yield {"type": "content", "text": text_delta}

            # Check for tool calls from the final message
            final = stream.get_final_message()
            if final.stop_reason == "tool_use":
                for block in final.content:
                    if block.type == "tool_use":
                        yield {
                            "type": "tool_call",
                            "id": block.id,
                            "name": block.name,
                            "arguments": json.dumps(block.input) if isinstance(block.input, dict) else str(block.input),
                        }

        yield {"type": "done"}

    def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet"),
            ModelInfo(id="claude-3-5-haiku-20241022", name="Claude 3.5 Haiku"),
            ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus"),
        ]
