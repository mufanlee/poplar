from dataclasses import dataclass, asdict
from enum import Enum
from typing import List
from datetime import datetime


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: Role
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role.value, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(role=Role(data["role"]), content=data["content"])


@dataclass
class Session:
    id: str
    title: str
    messages: List[Message] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_messages_for_api(self) -> List[dict]:
        return [msg.to_dict() for msg in self.messages]
