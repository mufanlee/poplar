"""Ollama provider — connects to local Ollama instance."""

import json
import logging
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any
from poplar.providers.base import ChatResponse, ModelInfo
from poplar.core.session import Message

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Provider for local Ollama models."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _api_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _format_messages(self, messages: List[Message]) -> list:
        return [msg.to_dict() for msg in messages]

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        import httpx
        api_messages = self._format_messages(messages)
        payload = dict(model=self.model, messages=api_messages, stream=False, **kwargs)
        resp = httpx.post(self._api_url("/v1/chat/completions"),
                          headers=self._headers(), json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ChatResponse(content=content, usage=usage)

    async def stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        import httpx
        api_messages = self._format_messages(messages)
        payload = dict(model=self.model, messages=api_messages, stream=True, **kwargs)
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", self._api_url("/v1/chat/completions"),
                                     headers=self._headers(), json=payload, timeout=120) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if delta.get("content"):
                            yield delta["content"]

    def stream_sync(self, messages: List[Message], tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Iterator[Dict[str, Any]]:
        """Stream with optional tool calling support using Ollama's OpenAI-compatible endpoint."""
        import httpx
        api_messages = self._format_messages(messages)
        payload = dict(model=self.model, messages=api_messages, stream=True, **kwargs)
        if tools:
            payload["tools"] = tools

        with httpx.Client() as client:
            with client.stream("POST", self._api_url("/v1/chat/completions"),
                               headers=self._headers(), json=payload, timeout=120) as resp:
                resp.raise_for_status()
                tool_calls: Dict[int, Dict] = {}

                for line in resp.iter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    chunk = json.loads(line[6:])
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    finish = chunk.get("choices", [{}])[0].get("finish_reason")

                    # Handle tool calls
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls:
                                tool_calls[idx] = {"id": tc.get("id", ""), "name": "", "arguments": ""}
                            if tc.get("id"):
                                tool_calls[idx]["id"] = tc["id"]
                            if tc.get("function", {}).get("name"):
                                tool_calls[idx]["name"] += tc["function"]["name"]
                            if tc.get("function", {}).get("arguments"):
                                tool_calls[idx]["arguments"] += tc["function"]["arguments"]

                    if delta.get("content"):
                        yield {"type": "content", "text": delta["content"]}

                    if finish == "tool_calls":
                        for tc in tool_calls.values():
                            yield {"type": "tool_call", **tc}

        yield {"type": "done"}

    def get_models(self) -> List[ModelInfo]:
        """Query Ollama server for available models, falling back to current model."""
        try:
            import httpx
            resp = httpx.get(self._api_url("/api/tags"), timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            if models:
                return [ModelInfo(id=m["name"], name=m.get("name", m["name"]))
                        for m in models]
        except Exception as e:
            logger.warning("Failed to fetch Ollama models: %s", e)
        return [
            ModelInfo(id=self.model, name=f"Ollama {self.model}"),
        ]
