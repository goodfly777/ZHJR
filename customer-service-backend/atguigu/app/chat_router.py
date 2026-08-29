import json
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from fastapi.params import Depends
from fastapi.responses import StreamingResponse

from atguigu.app.dependencies import get_dialogue_service
from atguigu.app.schemas import ChatRequest, ChatResponse, HistoryResponse, HistoryMessage, ChatMessage, ChatObject
from atguigu.domain.message import ProcessResult, UserMessage, MessageType, MessageObject
from atguigu.domain.state import DialogueState
from atguigu.service.dialogue_service import DialogueService

# 声明路由对象
chat_router = APIRouter()

# 定义API


@chat_router.post("/api/chat")
async def chat(
        chat_request: ChatRequest,
        dialogue_service: DialogueService = Depends(get_dialogue_service)) -> ChatResponse:

    # 定义两套模型：接口模型（ChatRequest、ChatResponse）、领域模型（业务模型 UserMessage、ProcessResult）
    # ChatRequest -> UserMessage
    # ProcessResult -> ChatResponse
    # DialogueService
    user_message: UserMessage = _build_user_message(chat_request)
    process_result: ProcessResult = await dialogue_service.process_message(user_message)
    chat_response: ChatResponse = _build_chat_response(process_result)
    return chat_response


@chat_router.get("/api/chat/state")
async def chat_state(
        sender_id: str,
        dialogue_service: DialogueService = Depends(get_dialogue_service)) -> dict:

    # 返回当前会话状态：活动任务、暂停任务、槽位、聚焦对象（需求 5.3 会话状态查询）
    state: DialogueState = await dialogue_service.get_state(sender_id)
    return _build_state_payload(state)


@chat_router.post("/api/chat/stream")
async def chat_stream(
        chat_request: ChatRequest,
        dialogue_service: DialogueService = Depends(get_dialogue_service)) -> StreamingResponse:

    # SSE 流式响应：将多轮 bot 消息逐条以 SSE 推送（事件名 message / done）
    async def event_generator():
        user_message: UserMessage = _build_user_message(chat_request)
        process_result: ProcessResult = await dialogue_service.process_message(user_message)
        for message in process_result.messages:
            payload = {"text": message.text, "object": _object_to_dict(message.object)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@chat_router.get("/api/chat/history")
async def history(
        sender_id: str,
        dialogue_service: DialogueService = Depends(get_dialogue_service)) -> HistoryResponse:

    state: DialogueState = await dialogue_service.get_state(sender_id)
    messages: list[HistoryMessage] = []

    for session in state.shared.sessions:
        for turn in session.turns:

            # 用户消息
            messages.append(
                HistoryMessage(
                    role="user",
                    text=turn.user_message.text,
                    object=ChatObject(**asdict(turn.user_message.object)) if turn.user_message.object is not None else None
                )
            )

            # 机器人消息
            messages.extend(
                 [
                     HistoryMessage(
                         role="bot",
                         text=message.text,
                         object=ChatObject(**asdict(message.object)) if message.object is not None else None
                     )
                    for message in turn.bot_messages
                 ]
            )

    return HistoryResponse(sender_id=sender_id, messages=messages)


def _build_user_message(chat_request: ChatRequest)-> UserMessage:

    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=chat_request.message_id or str(uuid.uuid4()),
        type = MessageType.TEXT if chat_request.text is not None else MessageType.OBJECT,
        text= chat_request.text,
        object = MessageObject(**chat_request.object.model_dump()) if chat_request.object is not None else None
    )

def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages = [
            ChatMessage(
                text = message.text,
                object = ChatObject(**asdict(message.object)) if message.object is not None else None
            ) for message in process_result.messages
        ]
    )


def _object_to_dict(obj: MessageObject | None) -> dict[str, Any] | None:
    if obj is None:
        return None
    return asdict(obj)


def _build_state_payload(state: DialogueState) -> dict[str, Any]:

    active = state.tasks.active
    paused = state.tasks.paused
    focused = state.shared.focused_object

    def task_dict(task) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "flow_id": task.flow_id,
            "step_id": task.step_id,
            "slots": task.slots,
        }

    return {
        "sender_id": state.sender_id,
        "active_task": task_dict(active) if active is not None else None,
        "paused_tasks": [task_dict(t) for t in paused],
        "focused_object": {
            "type": focused.type,
            "id": focused.id,
            "title": focused.title,
            "attributes": focused.attributes,
        } if focused is not None else None,
    }

