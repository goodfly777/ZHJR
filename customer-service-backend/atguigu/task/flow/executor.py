from atguigu.domain.message import BotMessage, UserMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.runner import ActionRunner, ActionCall
from atguigu.task.flow.conditions import ConditionEvaluator
from atguigu.task.flow.links import StaticLink, FallbackLink, ConditionalLink
from atguigu.task.flow.models import FlowCatalog
from atguigu.task.flow.steps import StartFlowStep, ResponseFlowStep, CollectSlotStep, ActionFlowStep, EndFlowStep, \
    FlowStep
from atguigu.task.response.renderer import ResponseRenderer


class FlowExecutor:

    def __init__(
            self,
            action_runner: ActionRunner,
            response_renderer: ResponseRenderer,
            condition_evaluator: ConditionEvaluator,
            max_steps_per_turn: int = 100) -> None:

        self.action_runner = action_runner
        self.response_renderer = response_renderer
        self.condition_evaluator = condition_evaluator
        self.max_steps_per_turn = max_steps_per_turn

    async def run_task(self, state: DialogueState, flows: FlowCatalog, user_message: UserMessage) -> list[BotMessage]:
        """按步骤推进流程的执行，并返回机器人回复结果列表"""

        messages: list[BotMessage] = []

        for _ in range(self.max_steps_per_turn):

            # 获取当前活跃任务
            task = state.tasks.active

            # 情况1：如果不存在活跃任务，则返回messages
            if task is None:
                return messages

            # 情况2：如果存在活跃任务，则根据当前活跃任务推进流程(执行每一个步骤，每个步骤执行策略不同，分别处理)
            # 获取流程
            flow = flows.get_flow(task.flow_id)
            # 获取步骤
            step = flow.get_step(task.step_id)

            if isinstance(step, StartFlowStep):

                # 推进流程到下一步
                self._advance(step, state)
                continue

            if isinstance(step, ResponseFlowStep):
                # 要回复的信息的组织
                message = await self.response_renderer.render(step.template, state, user_message)
                messages.append(message)

                # 推进流程到下一步
                self._advance(step, state)
                continue

            if isinstance(step, CollectSlotStep):

                # 搜集槽位信息
                should_wait = await self._run_collect_step(step, state, messages, user_message)

                # 如果需要等待用户输入
                if should_wait:
                    return messages

                # 如果不需要等待用户输入
                # 推进流程到下一步
                self._advance(step, state)
                continue

            if isinstance(step, ActionFlowStep):

                # 执行一个具体的动作
                action_call = ActionCall(action_name=step.action, action_kwargs=step.args)
                result = await self.action_runner.run(action_call, state)
                state.tasks.set_slots(result.slot_updates)

                # 推进流程到下一步
                self._advance(step, state)
                continue

            if isinstance(step, EndFlowStep):
                state.tasks.complete_active()
                return messages

    def _advance(self, step: FlowStep, state: DialogueState) -> None:

        for link in step.next:
            if isinstance(link, StaticLink):
                state.tasks.active.step_id = link.target
                return
            if isinstance(link, FallbackLink):
                state.tasks.active.step_id = link.target
                return
            if isinstance(link, ConditionalLink):
                if self.condition_evaluator.evaluate(link.condition, {"slots": state.tasks.active.slots}):
                    state.tasks.active.step_id = link.target
                    return

    async def _run_collect_step(
            self,
            step: CollectSlotStep,
            state: DialogueState,
            messages: list[BotMessage],
            user_message: UserMessage
    ) -> bool:

        #尝试填槽
        self._try_to_fill_slot_from_focused_object(step, state)

        # 获取活跃任务中的槽位值
        task = state.tasks.active
        value = task.slots.get(step.slot_name)

        # 槽位未填充
        if value is None or value == "":
            messages.append(
                await self.response_renderer.render(step.template, state, user_message)
            )

            # should_wait = True
            return True

        # 槽位已填充
        # validation是否已配置 且 条件表达式为假时 ， 则返回澄清话术（failure_template）
        if (
            step.validation
            and
            not self.condition_evaluator.evaluate(
                 step.validation.condition,
            {"slots": state.tasks.active.slots}
            )
        ):

            # 删除填充错误的槽位置
            state.tasks.remove_slot(step.slot_name)

            # 返回澄清结果
            messages.append(
                await self.response_renderer.render(step.validation.failure_template, state, user_message)
            )

            # should_wait = True
            return True

        # should_wait = False
        return False



    @staticmethod
    def _try_to_fill_slot_from_focused_object(step: CollectSlotStep, state: DialogueState) -> None:

        # 获取聚焦对象
        focused_object = state.shared.focused_object
        if focused_object is None:
            return

        # 金融业务对象 → 槽位映射（对齐 flow_config 槽位）
        type_to_slot = {
            "account": "account_no",
            "transaction": "related_txn_no",
            "loan": "loan_type",
            "card": "card_no",
        }

        if step.slot_name in type_to_slot.values() and focused_object.type in type_to_slot:
            if type_to_slot[focused_object.type] == step.slot_name:
                slots: dict[str, object] = {step.slot_name: focused_object.id}
                # 账户对象可能在 attributes 中携带 customer_no
                if focused_object.type == "account" and focused_object.attributes.get("customer_no"):
                    slots["customer_no"] = focused_object.attributes["customer_no"]
                state.tasks.set_slots(slots)
        
