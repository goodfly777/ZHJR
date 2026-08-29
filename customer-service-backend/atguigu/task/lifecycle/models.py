from dataclasses import dataclass
from typing import TypeAlias


@dataclass
class TaskRef:
    task_id: str
    flow_id: str

#dataclass
# class SuperTask:
#     pass

@dataclass
class TaskStarted:
    task: TaskRef


@dataclass
class TaskSwitched:
    previous: TaskRef
    current: TaskRef


@dataclass
class TaskResumed:
    task: TaskRef


@dataclass
class TaskCanceled:
    task: TaskRef

TaskEvent: TypeAlias = (
        TaskStarted
        | TaskSwitched
        | TaskResumed
        | TaskCanceled
)

def xyz() -> TaskEvent:
    pass


# def abc() -> TaskStarted | TaskSwitched | TaskResumed | TaskCanceled:
#     pass
#
#
# def abc() -> SuperTask:
#     pass