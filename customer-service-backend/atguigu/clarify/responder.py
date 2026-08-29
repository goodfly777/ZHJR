import json
from dataclasses import asdict
from tempfile import template

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.clients.llm_client import llm
from atguigu.domain.message import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.plan.models import ClarifyReason
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt


class ClarifyResponder:

    def build_clarify_responder(self, reason: ClarifyReason, state: DialogueState) -> str:

        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "你这次同时提到了多个方向。我们先处理一个，你想先办理业务还是先咨询金融信息呢？"

        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先提供相关的账户、交易或产品对象，我再继续帮你看。"

        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "你是想了解贷款产品、理财产品，还是账户存款、信用卡规则呢？"

        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先办理业务（如查账户、办贷款、信用卡挂失），还是先咨询金融信息呢？"

        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "你这次是想办理什么业务呢？比如查询账户余额、查询交易流水、申请贷款、信用卡挂失，或者提交投诉工单。"

        if reason is ClarifyReason.UNKNOWN_TASK_FLOW:
            return "当前系统无法执行这个业务。请问你要查询账户、查询交易、申请贷款，还是办理信用卡挂失？"

        if reason is ClarifyReason.INVALID_TASK_COMMAND:
            return "当前任务状态不支持这个操作，请告诉我你想开始、继续还是取消哪个业务。"

        if reason is ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT:
            return "我暂时无法识别这个咨询方向，你可以具体说说想了解哪类金融产品或业务。"

        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.shared.focused_object
            if focused_object is not None and focused_object.type == "account":
                return "我已经收到这个账户了。你想查询账户余额、交易流水，还是了解账户产品信息呢？"

            if focused_object is not None and focused_object.type == "transaction":
                return "我已经收到这笔交易了。你想了解交易详情，还是提交相关的投诉工单？"

            if focused_object is not None and focused_object.type in ("loan", "wealth"):
                return "我已经收到这个产品了。你想了解它的详细信息，还是办理相关业务？"


        return "我还需要再确认一下你的意思，你可以换个更具体的说法告诉我。"


    async def respond(self, state: DialogueState, user_message: UserMessage, reason: ClarifyReason) -> list[BotMessage]:

        user_message_str = HistoryBuilder.render_user_message(user_message)
        history = HistoryBuilder.build(state.shared.current_session().turns)
        clarify_message = self.build_clarify_responder(reason, state)
        focused_object = json.dumps(asdict(state.shared.focused_object), ensure_ascii=False) if state.shared.focused_object is not None else ""

        prompt_text = load_prompt("clarify_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()


        response = await chain.ainvoke({
            "reason": reason.value,
            "clarify_message": clarify_message,
            "focused_object": focused_object,
            "history": history,
            "user_message": user_message_str
        })

        return [BotMessage(text=response)]
