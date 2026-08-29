import json
from dataclasses import asdict, dataclass, field
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.clients.llm_client import llm
from atguigu.domain.message import UserMessage
from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.plan.models import TurnPlan
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt
from atguigu.task.flow.models import FlowCatalog


class TurnPlanner:

    async def predict(self,
          state: DialogueState,
          user_message: UserMessage,
          flow_catalog: FlowCatalog,
          knowledge_intents: dict[str, KnowledgeIntent]
    ) -> TurnPlan:

        # 构建提示词生成过程的七个变量
        prompt_inputs = self._build_prompt_inputs(
            state,
            user_message,
            flow_catalog,
            knowledge_intents,
        )

        # 调用大模型进行意图识别
        return await self._predict_from_prompt_inputs(prompt_inputs)

    def _build_prompt_inputs(
            self,
            state: DialogueState,
            user_message: UserMessage,
            flow_catalog: FlowCatalog,
            knowledge_intents: dict[str, KnowledgeIntent]
    ) -> dict[str, Any]:

        # 1. 对话历史
        history = HistoryBuilder.build(state.shared.current_session().turns)
        # 2. 用户当前轮次的消息
        user_message_str = HistoryBuilder.render_user_message(user_message)
        # 3. 系统中可用的流程
        flows_data = []
        for flow in flow_catalog.flows.values():
            flow_dict = asdict(flow)
            flow_dict.pop("steps", None)
            flows_data.append(flow_dict)
        available_flows_json = json.dumps(flows_data, ensure_ascii=False)
        # 4. 意图列表
        intents_data = [{"id": intent.id, "description": intent.description} for intent in knowledge_intents.values()]
        knowledge_intents_json = json.dumps(intents_data, ensure_ascii=False)
        # 5. 激活的任务
        active_task = state.tasks.active
        active_task_json = json.dumps(asdict(active_task), ensure_ascii=False) if active_task is not None else ""
        # 6. 挂起的任务
        paused_tasks = state.tasks.paused
        interrupted_tasks_json = json.dumps([asdict(paused_task) for paused_task in paused_tasks], ensure_ascii=False)
        # 7. 当前聚焦的对象
        focused_object = state.shared.focused_object
        focused_object_json = json.dumps(asdict(focused_object), ensure_ascii=False) if focused_object is not None else ""
        return {
            "available_flows_json": available_flows_json,
            "knowledge_intents_json": knowledge_intents_json,
            "active_task_json": active_task_json,
            "interrupted_tasks_json": interrupted_tasks_json,
            "focused_object_json": focused_object_json,
            "current_conversation": history,
            "user_message":user_message_str
        }

    async def _predict_from_prompt_inputs(self, prompt_inputs:dict[str, Any]) -> TurnPlan:

        prompt_text = load_prompt("turn_plan")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | JsonOutputParser()
        response = await chain.ainvoke(prompt_inputs)
        return TurnPlan.from_dict(response)

if __name__ == '__main__':

    # @dataclass
    # class A:
    #     id: int
    #     description: str
    #     steps:list[str] = field(default_factory=list)
    #
    # a = A(id=1, description="2", steps=["start", "end"])
    # print(a)
    # a_dict = asdict(a)
    # print(a_dict)

    list_data = [{"a": 1}, {"a": 2}, {"a": 3}]
    data= json.dumps(list_data, ensure_ascii=False)
    print(data)

