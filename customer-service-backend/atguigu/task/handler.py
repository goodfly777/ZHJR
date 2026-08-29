from atguigu.domain.message import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.command.models import Command
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.flow.executor import FlowExecutor
from atguigu.task.flow.models import FlowCatalog
from atguigu.task.lifecycle.responder import TaskLifecycleResponder


class TaskHandler:

    def __init__(
            self,
            command_processor: CommandProcessor,
            flows: FlowCatalog,
            flow_executor: FlowExecutor,
            lifecycle_responder: TaskLifecycleResponder,
    ) -> None:
        self.command_processor = command_processor
        self.flows = flows
        self.flow_executor = flow_executor
        self.lifecycle_responder = lifecycle_responder

    async def handle(
            self,
            commands: list[Command],
            state: DialogueState,
            user_message: UserMessage
    ) -> list[BotMessage]:
        # CommandProcessor：通过理解Command的意图，修改DialogueState，返回TaskEvent
        events = self.command_processor.run(commands, state, self.flows)
        # 使用TaskLifecycleResponder读取TaskEvent，返回合适的回复
        messages = self.lifecycle_responder.respond(events)
        # 读取DialogueState中的变化，根据其进行流程步骤的推进，在此过程中修改step_id，组织槽位信息slot
        bot_messages: list[BotMessage] = await self.flow_executor.run_task(state, self.flows, user_message)
        # 将消息组装起来
        messages.extend(bot_messages)
        return messages


if __name__ == '__main__':
    list1 = [1, 2, 3]
    list2 = [4, 5, 6]

    # list1.append(list2)
    list1.extend(list2)
    print(list1)
