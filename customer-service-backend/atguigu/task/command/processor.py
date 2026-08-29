from langgraph.func import task

from atguigu.domain.state import DialogueState, TaskInstance
from atguigu.task.command.models import Command, StartFlowCommand, SetSlotsCommand, CancelTaskCommand, ResumeTaskCommand
from atguigu.task.flow.models import FlowCatalog
from atguigu.task.lifecycle.models import TaskEvent


class CommandProcessor:
    """
    修改 全局会话状态 DialogueState
    返回 TaskEvent 提供给 TaskLifecycleResponder
    """

    def run(self, commands:list[Command], state: DialogueState, flows: FlowCatalog) -> list[TaskEvent]:

        events: list[TaskEvent] = []
        for command in commands:
            event = self._apply(command, state, flows)
            if event is not None:
                events.append(event)
        return events

    def _apply(self, command:Command, state: DialogueState, flows: FlowCatalog) -> TaskEvent | None:

        if isinstance(command, StartFlowCommand):
            # 根据 command.flow 获取flow对象
            flow = flows.get_flow(command.flow)
            # 根据flow对象获取流程的开始步骤id
            start_step_id = flow.get_start_step().id
            # 获取taskInstance实例
            task = TaskInstance(
                flow_id = flow.id,
                step_id = start_step_id
            )
            # 将任务启动（修改state的状态）
            return state.tasks.start(task)

        if isinstance(command, SetSlotsCommand):
            state.tasks.set_slots(command.slots)
            return None

        if isinstance(command, CancelTaskCommand):
            return state.tasks.cancel(command.task_id)

        if isinstance(command, ResumeTaskCommand):
            return state.tasks.resumed(command.task_id)

        return None