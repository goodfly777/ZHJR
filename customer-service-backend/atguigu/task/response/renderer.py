from typing import Any

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.message import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.task.response.models import ResponseTemplate, ResponseMode


class ResponseRenderer:

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    async def render(
            self,
            template: ResponseTemplate,
            state: DialogueState,
            user_message: UserMessage
    ) -> BotMessage:
        """按照模板的三种模式分别渲染最终的回复信息"""

        # STATIC：直接用槽位数据渲染静态的text文本，渲染后的结果就是BotMessage的内容
        if template.mode is ResponseMode.STATIC:
            rendered_text = Template(template.text).render(slots = state.tasks.active.slots)
            return BotMessage(text=rendered_text)

        # REPHRASE：将用户输入的text文本先用槽位数据进行渲染，然后使用prompt作为提示词，调用llm进行改写，改写后的结果就是BotMessage的内容
        if template.mode is ResponseMode.REPHRASE:
            rendered_text = Template(template.text).render(slots=state.tasks.active.slots)
            text = await self._call_llm(template.prompt, state, user_message, rendered_text)
            return BotMessage(text=text)

        # GENERATE：将prompt直接交给llm进行处理，直接按照prompt生成BotMessage的内容
        if template.mode is ResponseMode.GENERATE:

            text = await self._call_llm(template.prompt, state, user_message)
            return BotMessage(text=text)

    async def _call_llm(self, prompt: str, state: DialogueState, user_message: UserMessage, current_response = ""):
        """调用大模型生成回复文本"""

        # 加载jinja2模板
        prompt_template = PromptTemplate.from_template(prompt, template_format="jinja2")
        # 组装链
        chain = prompt_template | self.llm | StrOutputParser()

        # 获取聊天历史：history
        # 获取当前session
        session = state.shared.current_session()
        # 获取session下的turns
        turns = session.turns

        # 调用模型
        return await chain.ainvoke({
            "history": HistoryBuilder.build(turns),
            "user_message": HistoryBuilder.render_user_message(user_message),
            "current_response": current_response
        })
