from pydantic import BaseModel

# 前后端接口的对象模型封装一般使用pydantic.BaseModel
class ChatObject(BaseModel):
    """对象消息"""
    type: str # 必填，不需要写默认值，前端不传递数据的话，则pydantic的校验机制会报告错误，程序更健壮
    id: str
    title: str | None = None
    attributes: dict = {}

class ChatRequest(BaseModel):
    """聊天请求对象"""
    sender_id: str # 发送者ID
    text: str | None = None # 文本消息
    object: ChatObject | None = None # 对象消息
    message_id: str | None = None

class ChatMessage(BaseModel):
    """聊天消息响应对象"""
    text: str | None = None # 文本消息
    object: ChatObject | None = None # 对象消息


class ChatResponse(BaseModel):
    """聊天响应对象"""
    sender_id: str # 发送者ID
    message_id: str # 消息id
    messages: list[ChatMessage] # 本轮会话AI客服返回的消息列表

class HistoryMessage(BaseModel):
    """聊天历史消息对象"""
    role: str # user 或 bot
    text: str | None = None
    object: ChatObject | None = None

class HistoryResponse(BaseModel):
    """聊天历史响应对象"""
    sender_id: str # 发送者ID
    messages: list[HistoryMessage] # 聊天历史消息列表（包含用户和机器人的消息）



if __name__ == '__main__':

    c = ChatObject(type = "order", id = "001")

