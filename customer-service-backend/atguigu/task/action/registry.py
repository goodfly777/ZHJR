from atguigu.task.action.base import Action


class ActionRegistry:
    """Action注册表"""

    def __init__(self):
        """初始化注册表"""
        self._actions: dict[str, Action] = {}

    def register(self, action: Action) -> None:
        """注册Action"""
        self._actions[action.name] = action

    def get(self, name: str) -> Action:
        """根据Action的名字获取Action对象"""
        return self._actions[name]