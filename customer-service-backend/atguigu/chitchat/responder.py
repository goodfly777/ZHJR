from itertools import chain

from click import prompt
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.clients.llm_client import llm
from atguigu.domain.message import UserMessage, BotMessage
from atguigu.domain.state import Turn
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt


class ChitchatResponder:

    async def respond(self, user_message: UserMessage, recent_turns: list[Turn]) -> list[BotMessage]:

        prompt_text = load_prompt("chitchat_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()

        response = await chain.ainvoke({
            "history": HistoryBuilder.build(recent_turns),
            "user_message": HistoryBuilder.render_user_message(user_message)
        })

        return [BotMessage(text=response)]
