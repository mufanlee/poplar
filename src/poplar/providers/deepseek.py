import os
import openai
from typing import List, AsyncIterator
from poplar.providers.base import Provider, ChatResponse, ModelInfo
from poplar.core.session import Message


class DeepSeekProvider:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        # Clear proxy environment variables to avoid IPv6 parsing issues
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
            os.environ.pop(var, None)

        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        """Send messages to DeepSeek and get response."""
        api_messages = [msg.to_dict() for msg in messages]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            **kwargs
        )

        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return ChatResponse(content=content, usage=usage)

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream response from DeepSeek."""
        api_messages = [msg.to_dict() for msg in messages]

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_models(self) -> List[ModelInfo]:
        """Return available DeepSeek models."""
        return [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat"),
            ModelInfo(id="deepseek-coder", name="DeepSeek Coder"),
        ]
