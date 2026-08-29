from pathlib import Path

from atguigu.chitchat.handler import ChitchatHandler
from atguigu.chitchat.responder import ChitchatResponder
from atguigu.clarify.responder import ClarifyResponder
from atguigu.clients.llm_client import llm
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.knowledge.handler import KnowledgeHandler
from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
from atguigu.knowledge.providers import (
    FinanceLoanProductProvider,
    FinanceWealthProductProvider,
    FinanceAccountInfoProvider,
    FinanceFAQProvider,
)
from atguigu.knowledge.registry import KnowledgeProviderRegistry
from atguigu.knowledge.responder import KnowledgeResponder
from atguigu.plan.turn_planner import TurnPlanner
from atguigu.plan.validator import TurnPlanValidator
from atguigu.task.action.builder import build_action_runner
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.flow.conditions import ConditionEvaluator
from atguigu.task.flow.executor import FlowExecutor
from atguigu.task.flow.loader import FlowLoader
from atguigu.task.handler import TaskHandler
from atguigu.task.lifecycle.responder import TaskLifecycleResponder
from atguigu.task.response.renderer import ResponseRenderer

_FLOW_CONFIG_FILE = Path(__file__).parents[2] / "flow_config" / "user_flows.yml"


def build_dialogue_engine() -> DialogueEngine:
    flows = FlowLoader().load(_FLOW_CONFIG_FILE)
    action_runner = build_action_runner()
    response_renderer = ResponseRenderer(llm = llm)

    return DialogueEngine(
        turn_planner=TurnPlanner(),
        task_handler=TaskHandler(
            command_processor = CommandProcessor(),
            flows =  flows,
            flow_executor =FlowExecutor(
                action_runner = action_runner,
                response_renderer= response_renderer,
                condition_evaluator =  ConditionEvaluator()
            ),
            lifecycle_responder = TaskLifecycleResponder(
                flows = flows
            ),
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            provider_registry=KnowledgeProviderRegistry(
                [
                    FinanceLoanProductProvider(),
                    FinanceWealthProductProvider(),
                    FinanceAccountInfoProvider(),
                    FinanceFAQProvider(),
                ]
            ),
            knowledge_responder=KnowledgeResponder()
        ),
        chitchat_handler=ChitchatHandler(
            responder=ChitchatResponder()
        ),
        clarify_responder=ClarifyResponder(),
        turn_plan_validator=TurnPlanValidator(),
    )