from dataclasses import dataclass, field
from enum import Enum

from atguigu.task.command.models import Command


@dataclass
class TaskTurnPlan:
    commands: list[Command] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskTurnPlan":
        return cls(commands=[Command.from_dict(command) for command in data["commands"]])

@dataclass
class KnowledgeTurnPlan:
    intents: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeTurnPlan":
        return cls(intents = data["intents"])


@dataclass
class ChitchatPlan:
    pass

@dataclass
class TurnPlan:
    task: TaskTurnPlan | None = None
    knowledge: KnowledgeTurnPlan | None = None
    chitchat: ChitchatPlan | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TurnPlan":
        return cls(
            task=TaskTurnPlan.from_dict(data["task"]) if data.get("task") is not None else None,
            knowledge=KnowledgeTurnPlan.from_dict(data["knowledge"]) if data.get("knowledge") is not None else None,
            chitchat=ChitchatPlan() if data.get("chitchat") is not None else None
        )

class ClarifyReason(str, Enum):
    UNKNOWN_TASK_FLOW = "unknown_task_flow"
    MISSING_TRACK = "missing_track"
    MULTIPLE_TRACKS = "multiple_tracks"
    MISSING_TASK_COMMANDS = "missing_task_commands"
    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"

    # 聚焦对象和意图识别不匹配或聚焦对象不存在
    MISSING_FOCUSED_OBJECT = "missing_focused_object"
    OBJECT_REQUIRES_INTENT = "object_requires_intent"
    INVALID_TASK_COMMAND = "invalid_task_command"
    UNKNOWN_KNOWLEDGE_INTENT = "unknown_knowledge_intent"

@dataclass
class TurnPlanValidationResult:

    valid: bool
    reason: ClarifyReason | None = None


if __name__ == '__main__':
    # data = {"intents": ["intent1", "intent2"]}
    # obj = KnowledgeTurnPlan(intents = data["intents"])
    # print(obj)

    data = {
        "commands": [
            {"command": "start_flow", "flow": "lookup_order_status"},
            {"command": "cancel_task", "task_id": "abc123"}
        ]
    }
    obj = TaskTurnPlan(commands=[Command.from_dict(command) for command in data["commands"]])
    print(obj)
