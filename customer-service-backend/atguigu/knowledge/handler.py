import asyncio

from atguigu.domain.message import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.knowledge.registry import KnowledgeProviderRegistry
from atguigu.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:

    def __init__(
            self,
            knowledge_intents: dict[str, KnowledgeIntent],
            provider_registry: KnowledgeProviderRegistry,
            knowledge_responder: KnowledgeResponder,
    ) -> None:
        self.knowledge_intents = knowledge_intents
        self.provider_registry = provider_registry
        self.knowledge_responder = knowledge_responder

    async def handle(
            self,
            intents: list[str],
            state: DialogueState,
            user_message: UserMessage
    ) -> list[BotMessage]:

        # 根据意图列表查找provider_id列表
        provider_ids = self._get_provider_ids_by_intents(intents)

        # 查询知识库
        retrieve_coroutines = []
        for provider_id in provider_ids:
            provider = self.provider_registry.get(provider_id)
            retrieve_coroutines.append(provider.retrieve(state, user_message))

        # 并发调用：* 列表解包，相当于  asyncio.gather(协程1，协程2)
        # [[],[],[]]
        knowledge_chunks = await asyncio.gather(*retrieve_coroutines)

        # 组装：嵌套循环 => chunks
        # chunks = []
        # for current_chunks in knowledge_chunks:
        #     for chunk in current_chunks:
        #         chunks.append(chunk)

        # 组装：单层循环 => chunks
        # chunks = []
        # for current_chunks in knowledge_chunks:
        #     chunks.extend(current_chunks)

        # 组装：嵌套列表推导式 => chunks
        chunks = [chunk for current_chunks in knowledge_chunks for chunk in current_chunks]


        # 调用模型
        return await self.knowledge_responder.respond(
            user_message=user_message,
            current_turns=state.shared.current_session().turns,
            chunks = chunks
        )


    def _get_provider_ids_by_intents(self, intents: list[str]) -> list[str]:

        # 根据意图字符串列表获取provider_id列表
        provider_ids: list[str] = []
        for intent in intents:
            provider_ids.extend(self.knowledge_intents[intent].provider_ids)

        # 去重
        return list(set(provider_ids))

