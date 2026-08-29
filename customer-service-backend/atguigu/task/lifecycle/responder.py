from langchain_protocol import TasksEvent

from atguigu.domain.message import BotMessage
from atguigu.task.flow.models import FlowCatalog
from atguigu.task.lifecycle.models import TaskStarted, TaskSwitched, TaskResumed, TaskCanceled, TaskRef


class TaskLifecycleResponder:

    def __init__(self , flows: FlowCatalog) -> None:
        self.flows = flows


    def respond(self, events: list[TasksEvent]) -> list[BotMessage]:
        """根据TaskEvent列表返回AI客服的回复消息列表"""

        messages: list[BotMessage] = []
        for event in events:
            messages.append(self._message_for(event))
        return messages


    def _message_for(self, event: TasksEvent):
        """根据TaskEvent返回AI客服的回复消息"""

        if isinstance(event, TaskStarted):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(text=f"好的，我们先处理{flow_name}")

        if isinstance(event, TaskSwitched):
            previous_name = self._flow_name(event.previous.flow_id)
            current_name = self._flow_name(event.current.flow_id)
            return BotMessage(text=f"好的，我们先把{previous_name}放一放，先处理{current_name}")

        if isinstance(event, TaskResumed):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(text=f"好的，我们继续之前的{flow_name}")

        if isinstance(event, TaskCanceled):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(text=f"好的，我帮你取消{flow_name}")

        raise TypeError(f"Unknown event type: {type(event).__name__}")

    def _flow_name(self, flow_id: str) -> str:

        flow = self.flows.get_flow(flow_id)

        # 防御性编程
        return flow.name or flow.id


if __name__ == '__main__':

    ts = TaskStarted(TaskRef(
        task_id="123",
        flow_id="456"
    ))

    print(type(ts).__name__)
    print(type(ts))