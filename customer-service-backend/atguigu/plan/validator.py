from aiomysql.sa.result import ResultMetaData
from langgraph.constants import START

from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.plan.models import TurnPlanValidationResult, TurnPlan, ClarifyReason
from atguigu.task.command.models import StartFlowCommand, CancelTaskCommand, ResumeTaskCommand, SetSlotsCommand
from atguigu.task.flow.models import FlowCatalog


class TurnPlanValidator:

    def validate(
            self,
            turn_plan: TurnPlan,
            state: DialogueState,
            flow_catalog: FlowCatalog,
            knowledge_intents: dict[str,KnowledgeIntent]
    ) -> TurnPlanValidationResult:

        # 判断结果中一共识别出借条轨道
        active_tracks = self._active_tracks(turn_plan)

        # 如果一条没有被识别出来，则返回失败
        if not active_tracks:
            return self._reject(ClarifyReason.MISSING_TRACK)

        # 如果有多个轨道被识别出来，则返回失败
        if len(active_tracks) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS)

        # 只有一个方向，将其取出
        track = active_tracks[0]
        if track == "task":
            return self._validate_task(turn_plan, state, flow_catalog)

        if track == "knowledge":
            return self._validate_knowledge(turn_plan, state, knowledge_intents)

        # 无需处理
        # if track == "chitchat":
        #     pass

        # 校验通过
        return TurnPlanValidationResult(valid=True)


    @staticmethod
    def _active_tracks(turn_plan: TurnPlan) -> list[str]:
        active_tracks: list[str] = []
        if turn_plan.task is not None:
            active_tracks.append("task")

        if turn_plan.knowledge is not None:
            active_tracks.append("knowledge")

        if turn_plan.chitchat is not None:
            active_tracks.append("chitchat")

        return active_tracks

    def _reject(self, reason: ClarifyReason) -> TurnPlanValidationResult:
        return TurnPlanValidationResult(valid=False, reason=reason)

    def _validate_task(
            self,
            turn_plan: TurnPlan,
            state: DialogueState,
            flow_catalog: FlowCatalog
    ) -> TurnPlanValidationResult:
        """校验Task轨道"""
        task_plan = turn_plan.task

        # 有task，但是task里面没有commands
        if not task_plan.commands:
            return self._reject(ClarifyReason.MISSING_TASK_COMMANDS)

        for command in task_plan.commands:
            if isinstance(command, StartFlowCommand):

                # 当task_plan中识别的业务流程的名字不在系统定义的流程集合中时，则不合法
                if  command.flow not in flow_catalog.flows:
                    return self._reject(ClarifyReason.UNKNOWN_TASK_FLOW)

            if isinstance(command, CancelTaskCommand):

                # 被取消的任务必须在 挂起任务列表中 或是 正在执行的任务
                # 挂起任务列表的task_ids
                paused_task_ids = [paused_task.task_id for paused_task in state.tasks.paused]
                # 正在执行的任务的task_id
                active_task_id = state.tasks.active.task_id
                # 所有任务的task_ids
                all_tasks_ids = paused_task_ids + [active_task_id]
                # 判断意图识别结果中的task_id是否在所有以上id之中
                if command.task_id not in all_tasks_ids:
                    return self._reject(ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command, ResumeTaskCommand):
                # 被回复的任务必须在 挂起任务列表中
                # 挂起任务列表的task_ids
                paused_task_ids = [paused_task.task_id for paused_task in state.tasks.paused]
                # 判断意图识别结果中的task_id是否在挂起任务列表中
                if command.task_id not in paused_task_ids:
                    return self._reject(ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command, SetSlotsCommand):
                if not command.slots:
                    return self._reject(ClarifyReason.INVALID_TASK_COMMAND)

                for slot_name in command.slots.keys():
                    if slot_name not in flow_catalog.slots:
                        return self._reject(ClarifyReason.INVALID_TASK_COMMAND)

        # 校验通过
        return TurnPlanValidationResult(valid=True)


    def _validate_knowledge(
            self,
            turn_plan: TurnPlan,
            state: DialogueState,
            knowledge_intents: dict[str, KnowledgeIntent]
    ) -> TurnPlanValidationResult:

        knowledge_plan = turn_plan.knowledge

        # 有knowledge，但是knowledge中没有识别出具体的intents
        if not knowledge_plan.intents:
            return self._reject(ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        # 有knowledge，knowledge中也识别出了具体的intents，但是不是系统中支持的intents
        for intent_id in knowledge_plan.intents:
            intent = knowledge_intents.get(intent_id)
            if intent is None:
                return self._reject(ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT)

            # 如果获取到的对应的intent
            # 模型识别用户意图涉及的对象
            requires_object = intent.requires_object
            # 用户实际选择的对象
            focused_object = state.shared.focused_object
            if requires_object is not None and (focused_object is None or focused_object.type != requires_object):
                return self._reject(ClarifyReason.MISSING_FOCUSED_OBJECT)

        # 校验通过
        return TurnPlanValidationResult(valid=True)


if __name__ == '__main__':

    ids = [1,2,3]
    a = 4
    print(ids + [a])