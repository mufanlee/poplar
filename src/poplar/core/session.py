from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: Role
    content: str = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"role": self.role.value}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
            d["content"] = self.content or None
        else:
            d["content"] = self.content or ""
        if self.tool_call_id or self.role == Role.TOOL:
            d["tool_call_id"] = self.tool_call_id or ""
        if self.name:
            d["name"] = self.name
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            role=Role(data["role"]),
            content=data.get("content") or "",
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
        )


@dataclass
class Session:
    id: str
    title: str
    messages: Optional[List[Message]] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_message(self, message: Message):
        if self.messages is None:
            self.messages = []
        self.messages.append(message)

    def get_messages_for_api(self) -> list:
        if self.messages is None:
            return []
        return [msg.to_dict() for msg in self.messages]
