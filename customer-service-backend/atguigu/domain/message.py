from dataclasses import dataclass, field
from enum import Enum


@dataclass
class MessageObject:
    type: str
    id: str
    title: str | None = None
    attributes: dict = field(default_factory=dict)

class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    OBJECT = "object"

@dataclass
class UserMessage:
    """业务层使用的用户消息对象"""
    sender_id: str  # 发送者ID
    message_id: str  # 消息id
    type: MessageType
    text: str | None = None  # 文本消息
    object: MessageObject | None = None  # 对象消息


@dataclass
class BotMessage:
    """业务层使用的机器人消息对象"""
    text: str | None = None  # 文本消息
    object: MessageObject | None = None  # 对象消息

@dataclass
class ProcessResult:
    """业务层的响应对象"""
    sender_id: str
    message_id: str
    messages: list[BotMessage]



if __name__ == '__main__':
    user_message = UserMessage(
        sender_id="123",
        message_id="456",
        type=MessageType.TEXT,
        text="Hello, how are you?"
    )
