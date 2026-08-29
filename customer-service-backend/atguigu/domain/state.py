import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from atguigu.domain.message import UserMessage, BotMessage
from atguigu.task.lifecycle.models import TaskRef, TaskStarted, TaskSwitched, TaskEvent, TaskCanceled, TaskResumed


@dataclass
class Turn:
    """一轮对话"""
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage] = field(default_factory=list)

    @classmethod
    def create(cls, user_message):
        return cls(
            turn_id=str(uuid.uuid4()),
            user_message=user_message,
            bot_messages=[]
        )


@dataclass
class Session:
    """会话"""
    session_id: str
    started_at: float
    last_activity_at: float
    closed_at: float | None = None
    turns: list[Turn] = field(default_factory=list)

    @classmethod
    def create(cls) -> "Session":
        now = time.time()
        return cls(session_id=str(uuid.uuid4()), started_at=now, last_activity_at=now)

    def close(self) -> None:
        self.closed_at = time.time()

    def append_turn(self, turn):
        self.turns.append(turn)
        self.last_activity_at = time.time()


@dataclass
class FocusedObject:
    """聚焦对象"""
    type: str
    id: str
    title: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SharedState:
    focused_object: FocusedObject | None = None
    sessions: list[Session] = field(default_factory=list)

    #@property
    def current_session(self) -> Session:
        """获取当前session对象"""
        if not self.sessions:
            return None
        return self.sessions[-1]

    def start_session(self) -> Session:
        session = Session.create()
        self.sessions.append(session)
        return session

    def close_current_session(self) -> None:
        session = self.current_session()
        if session is not None:
            session.close()

    def clear_focus(self) -> None:
        self.focused_object = None

    def append_turn(self, turn):
        session = self.current_session()
        session.append_turn(turn)


@dataclass
class TaskInstance:
    """任务实例"""
    flow_id: str
    step_id: str | None = None
    slots: dict[str, Any] = field(default_factory=dict)

    # 使用lambda的形式定义复杂函数的匿名引用
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_ref(self) -> TaskRef:
        """将TaskInstance对象转换成TaskRef对象"""
        return TaskRef(task_id=self.task_id, flow_id=self.flow_id)



@dataclass
class TaskState:
    """任务相关的状态信息"""
    active: TaskInstance | None = None
    paused: list[TaskInstance] = field(default_factory=list)

    def start(self, task: TaskInstance) -> TaskEvent:

        # 情况1：当active中没有活跃任务时（active是空值）
        # 直接将要开启的新任务存储在 active 中
        if self.active is None:
            self.active = task
            task_ref = task.to_ref()
            return TaskStarted(task = task_ref)

        # 情况2：当active中已经有任务正在执行了
        # 那么先将这个正在执行的任务放入paused
        # 然后将要开启的新任务存储在 active 中
        previous = self.active
        self.paused.append(previous)
        self.active = task
        return TaskSwitched(
            previous=previous.to_ref(),
            current=task.to_ref()
        )

    def cancel(self, task_id: str) -> TaskCanceled:

        # 情况1： 要取消的任务就是当前正在执行的任务（active）
        # 直接将active置空，表示现在没有正在执行的任务了
        if self.active is not None and self.active.task_id == task_id:
            canceled = self.active
            self.active = None # 取消任务
            return TaskCanceled(task=canceled.to_ref())

        # 情况2：要取消的是暂停列表中的任务（paused）
        # 去暂停列表中找对应的任务，如果找到怎就将这个任务记录下来
        canceled = None
        for task in self.paused:
            if task.task_id == task_id:
                canceled = task
                break

        # 如果找到任务则将其从列表中移除，表示这个任务被取消了
        if canceled is not None:
            self.paused.remove(canceled)
            return TaskCanceled(task=canceled.to_ref())

        # 情况3：要取消的任务没找到
        # 说明这个任务不存在，抛出异常，提醒上层处理
        raise ValueError(f"Task {task_id} not found")

    def resumed(self, task_id: str) -> TaskEvent:

        # 第一步：从paused中找到要回复的那个任务
        target = next(task for task in self.paused if task.task_id == task_id)
        self.paused.remove(target)

        # 情况1：当前没有任务在执行（active是空的）
        # 将恢复的任务直接放入active
        if self.active is None:
            self.active = target
            return TaskResumed(task=target.to_ref())

        # 情况2：当前有任务在执行（active不是空的）
        # 将正在执行的任务放入暂停任务列表
        previous = self.active
        self.paused.append(previous)
        # 将要恢复的任务放入active
        self.active = target
        return TaskSwitched(
            previous=previous.to_ref(),
            current=target.to_ref()
        )

    def set_slots(self, slots: dict[str, Any]) -> None:
        self.active.slots.update(slots)

    def complete_active(self) -> None:
        self.active = None

    def remove_slot(self, slot_name: str) -> None:

        # None：如果slots中不存在slot_name，则不排除异常，而是返回None
        self.active.slots.pop(slot_name, None)

    def reset(self):
        # 清空活跃任务
        self.active = None
        # 清空挂起的任务
        self.paused.clear()


@dataclass
class DialogueState:
    """会话上下文的状态信息"""
    sender_id: str
    shared: SharedState = field(default_factory=SharedState)
    tasks: TaskState = field(default_factory=TaskState)

    def reset_runtime_state_for_new_session(self) -> None:
        # 清理任务
        self.tasks.reset()
        # 清理聚焦对象
        self.shared.clear_focus()


if __name__ == '__main__':


    d1 = {}
    d1.update({"key1": "value1"})
    print(d1)
    d1.update({"key2": "value2"})
    print(d1)
    d1.update({"key1": "value3"})
    print(d1)
