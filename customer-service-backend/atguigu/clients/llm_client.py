from typing import Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from atguigu.conf.config import settings

# v1：llm客户端模块在程序启动是，当前脚本只要被引用，则llm直接实例化：预加载
# 初始化各种类型的客户端对象
llm: BaseChatModel = init_chat_model(
    model=settings.llm_model,
    model_provider='openai',
    api_key=settings.llm_api_key,
    temperature=0,
    base_url=settings.llm_base_url
)

# v2：全局单例模式
# 1. 全局单例缓存：延迟加载
# 2. BaseChatModel： 面向接口编程，使用父类类型声明，避免模型切换时，新的模型没有旧的模型的特殊的方法，导致系统崩溃
_llm_instance: Optional[BaseChatModel] = None

def get_llm() -> BaseChatModel:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = init_chat_model(
            model=settings.llm_model,
            model_provider='openai',
            api_key=settings.llm_api_key,
            temperature=0,
            base_url=settings.llm_base_url
        )
    return _llm_instance


if __name__ == '__main__':

    def chat_task():
        llm = get_llm()
        response = llm.invoke("你好")
        return response.content

    result = chat_task()
    print(result)