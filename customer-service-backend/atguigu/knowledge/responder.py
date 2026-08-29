from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.clients.llm_client import llm
from atguigu.domain.message import UserMessage, BotMessage
from atguigu.domain.state import Turn
from atguigu.knowledge.providers import KnowledgeChunk
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt


class KnowledgeResponder:

    async def respond(
            self,
            user_message: UserMessage,
            current_turns: list[Turn],
            chunks: list[KnowledgeChunk]
    ) -> list[BotMessage]:

        # 获取提示词模板
        prompt_text = load_prompt("knowledge_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        # 创建链式调用结构
        chain = prompt | llm | StrOutputParser()

        user_message_str = HistoryBuilder.render_user_message(user_message)
        history = HistoryBuilder.build(current_turns)
        knowledge_content = "\n\n".join(chunk.content for chunk in chunks)

        response = await chain.ainvoke({
            "user_message": user_message_str,
            "history": history,
            "knowledge_content": knowledge_content
        })

        return [BotMessage(text=response)]
