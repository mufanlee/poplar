from typing import Protocol, List, AsyncIterator, Iterator, Dict, Any
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

    def stream_sync(self, messages: List[Message], tools: List[Dict[str, Any]] = None, **kwargs) -> Iterator[Dict[str, Any]]:
        """Synchronous streaming with optional tool calling support.
        
        Yields dicts:
        - {"type": "content", "text": "..."}
        - {"type": "tool_call", "id": "...", "name": "...", "arguments": "..."}
        - {"type": "done"}
        """
        ...

    def get_models(self) -> List[ModelInfo]:
        """Get available models."""
        ...
