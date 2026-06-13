from typing import Protocol, List, AsyncIterator
from poplar.core.session import Message


class ChatResponse:
    def __init__(self, content: str, usage: dict = None):
        self.content = content
        self.usage = usage or {}


class ModelInfo:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class Provider(Protocol):
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        """Send messages and get response."""
        ...

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream response chunks."""
        ...

    def get_models(self) -> List[ModelInfo]:
        """Get available models."""
        ...
