import importlib
import inspect
import pkgutil

from atguigu.clients.http_client import init_http_client, close_http_client
from atguigu.domain.state import DialogueState, TaskState, TaskInstance
from atguigu.task.action.base import Action
from atguigu.task.action.registry import ActionRegistry
from atguigu.task.action.runner import ActionRunner, ActionCall


def register_custom_actions(
        registry: ActionRegistry,
) -> None:
    """
    Python的类的自动发现机制：
    扫描指定的包，完成Action的子类的自动注册
    """

    package = importlib.import_module("atguigu.task.action.custom")

    # 在 package.__path__ 路径下，遍历所有以  {package.__name__}. 为前缀的模块
    # print(pkgutil.iter_modules(package.__path__, prefix=f"{package.__name__}."))

    for _, module_name, is_package in pkgutil.iter_modules(package.__path__, prefix=f"{package.__name__}."):

        # is_package： 不能是一个包
        if is_package:
            continue

        # inspect.isclass： 必须是一个类
        module = importlib.import_module(module_name)
        for _, action_class in inspect.getmembers(module, inspect.isclass):

            # 必须是Action的子类，不能是Action自己
            if not issubclass(action_class, Action) or action_class is Action:
                continue

            # 必须是当前模块中声明的类
            if action_class.__module__ != module.__name__:
                continue

            # 注册这个类
            registry.register(action_class())

def build_action_runner() -> ActionRunner:
    # 初始化注册表
    registry = ActionRegistry()
    # 注册action
    register_custom_actions(registry)
    # 返回ActionRunner
    return ActionRunner(registry)

if __name__ == '__main__':

    async def main():

        init_http_client()

        action_runner = build_action_runner()
        action_call = ActionCall(
            action_name="action_lookup_order_status",
            action_kwargs={}
        )
        state = DialogueState(
            sender_id="u1001",
            tasks=TaskState(
                active=TaskInstance(
                    flow_id="order_status_query",
                    step_id="lookup_order_status",
                    slots={"order_number": "A20260410001"}
                )
            )
        )
        result = await action_runner.run(action_call, state)
        print(result)

        await close_http_client()

    import asyncio
    asyncio.run(main())

