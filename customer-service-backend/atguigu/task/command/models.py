from dataclasses import dataclass
from typing import Any


@dataclass
class Command:
    command: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Command":
        command_class = COMMAND_NAME_TO_CLASS[data["command"]]
        return command_class(**data)



@dataclass
class StartFlowCommand(Command):
    flow: str


@dataclass
class SetSlotsCommand(Command):
    slots: dict[str, Any]


@dataclass
class CancelTaskCommand(Command):
    task_id: str


@dataclass
class ResumeTaskCommand(Command):
    task_id: str

COMMAND_NAME_TO_CLASS: dict[str, type[Command]] = {
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_task": CancelTaskCommand,
    "resume_task": ResumeTaskCommand,
}

if __name__ == '__main__':

    commands_dict_list = [
      {"command": "start_flow", "flow": "order_status_query"},
      {"command": "set_slots", "slots": {"order_number": "10001"}}
    ]

    # commands_dict_list = [
    #     {"command": "cancel_task", "flow": "order_status_query"},
    # ]

    # commands_dict_list = [
    #     {"command": "set_slots", "slots": {"order_number": "10001"}}
    # ]

    commands_obj_list: list[Command] = [Command.from_dict(command) for command in commands_dict_list]
    print(commands_obj_list)