import time
from dataclasses import asdict

from atguigu.chitchat.handler import ChitchatHandler
from atguigu.clarify.responder import ClarifyResponder
from atguigu.domain.message import UserMessage, ProcessResult, BotMessage, MessageType
from atguigu.domain.state import DialogueState, Turn, FocusedObject
from atguigu.knowledge.handler import KnowledgeHandler
from atguigu.plan.models import TurnPlan, TurnPlanValidationResult, ClarifyReason
from atguigu.plan.turn_planner import TurnPlanner
from atguigu.plan.validator import TurnPlanValidator
from atguigu.task.command.models import SetSlotsCommand
from atguigu.task.flow.models import FlowCatalog
from atguigu.task.flow.steps import CollectSlotStep
from atguigu.task.handler import TaskHandler


class DialogueEngine:

    def __init__(
            self,
            turn_planner: TurnPlanner,
            task_handler: TaskHandler,
            knowledge_handler: KnowledgeHandler,
            chitchat_handler: ChitchatHandler,
            clarify_responder: ClarifyResponder,
            turn_plan_validator: TurnPlanValidator,
    ) -> None:

        self.turn_planner = turn_planner
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder
        self.turn_plan_validator = turn_plan_validator

    async def process_message(self, state: DialogueState, user_message: UserMessage) -> ProcessResult:

        # 1. 准备session(新session、已有session、session过期)
        self._prepare_session(state)

        # 2. 使用用户消息创建本轮 Turn
        turn: Turn = Turn.create(user_message)

        # 3. 判断是文本消息还是对象消息
        if user_message.type is MessageType.TEXT:
            # 处理文本消息
            messages: list[BotMessage] = await self._handle_text_message(state, user_message)
        else:
            # 处理对象消息
            messages: list[BotMessage] = await self._handle_object_message(state, user_message)

        # 4. 将本轮产生的客服消息写入turn(提交turn，将turn存入session)
        turn.bot_messages.extend(messages)
        # 5. 将完整的turn加入当前的session
        state.shared.append_turn(turn)

        # 6. 返回包含本轮客服消息的ProcessResult
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages,
        )

    def _prepare_session(self, state: DialogueState) -> None:

        # 获取当前会话（session）
        session = state.shared.current_session()

        # 判断session是否存在
        if session is None:
            # 当前没有会话，需要创建一个新的会话
            state.shared.start_session()
        elif time.time() - session.last_activity_at > 60 * 60:
            # 会话最后一次活动时间距离现在已经超过1小时，关闭当前会话，开始一个新的会话
            state.shared.close_current_session()
            state.reset_runtime_state_for_new_session()
            state.shared.start_session()

    async def _handle_text_message(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:

        # 计划生成
        turn_plan: TurnPlan = await self.turn_planner.predict(
            state,
            user_message,
            self.task_handler.flows,
            self.knowledge_handler.knowledge_intents
        )

        # 计划校验
        validation: TurnPlanValidationResult = self.turn_plan_validator.validate(
            turn_plan,
            state,
            self.task_handler.flows,
            self.knowledge_handler.knowledge_intents
        )

        # 计划澄清
        if not validation.valid:
            return await self.clarify_responder.respond(state, user_message, validation.reason)

        # 执行计划（三路）
        if turn_plan.task is not None:
            return await self.task_handler.handle(turn_plan.task.commands, state, user_message)

        if turn_plan.knowledge is not None:
            return await self.knowledge_handler.handle(turn_plan.knowledge.intents, state, user_message)

        return await self.chitchat_handler.handle(state, user_message)

    async def _handle_object_message(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:

        # 记录聚焦对象
        # state.shared.focused_object = FocusedObject(
        #         type=user_message.object.type,
        #         id=user_message.object.id,
        #         title=user_message.object.title,
        #         attributes=dict(
        #             user_message.object.attributes
        #         ),
        #     )
        # asdict()做对象转字典的类型转换只试用于 用@dataclass装饰的类
        state.shared.focused_object = FocusedObject(**asdict(user_message.object))

        # 生成SetSlotsCommand
        command: SetSlotsCommand = self._object_slot_command(user_message, state, self.task_handler.flows)

        # 无法填槽
        if command is None:
            # 回复澄清信息
            return await self.clarify_responder.respond(state, user_message, ClarifyReason.OBJECT_REQUIRES_INTENT)

        # 匹配填槽条件
        return await self.task_handler.handle([command], state, user_message)

    def _object_slot_command(self, user_message: UserMessage, state: DialogueState, flows: FlowCatalog) -> SetSlotsCommand | None:

        # 获取槽位名称
        collect_slot_name = self._current_collect_slot_name(state, flows)
        if collect_slot_name is None:
            return None

        # 金融业务对象 → 槽位映射
        object_type = user_message.object.type
        object_id = user_message.object.id

        # 对象类型 → 可填充的槽位名（对齐 flow_config 槽位）
        type_to_slot = {
            "account": "account_no",
            "transaction": "related_txn_no",
            "loan": "loan_type",
            "wealth": "loan_type",  # 理财对象无专属申请流程，落到知识咨询
            "card": "card_no",
        }

        slot_name = type_to_slot.get(object_type)
        if slot_name is not None and collect_slot_name == slot_name:
            # 特殊处理：账户对象同时可能携带 customer_no（前端在 attributes 中带）
            slots: dict[str, str] = {slot_name: object_id}
            attrs = user_message.object.attributes or {}
            if attrs.get("customer_no") and collect_slot_name == "account_no":
                slots["customer_no"] = attrs["customer_no"]
            return SetSlotsCommand(command="set_slots", slots=slots)

        return None

    def _current_collect_slot_name(self, state: DialogueState, flows: FlowCatalog) -> str | None:

        # 判断当前是否有正在执行中的任务
        active_task = state.tasks.active
        if active_task is None:
            return None

        # 获取当前任务所在的流程对象
        current_flow = flows.get_flow(active_task.flow_id)
        # 获取当前的步骤对象
        current_step = current_flow.get_step(active_task.flow_id)
        if not isinstance(current_step, CollectSlotStep):
            return None
        return current_step.slot_name


