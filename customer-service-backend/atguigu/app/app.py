from contextlib import asynccontextmanager

from fastapi import FastAPI
from atguigu.app.chat_router import chat_router
from atguigu.app.dependencies import init_dialogue_engine
from atguigu.clients.database import init_db_engine, close_db_engine
from atguigu.clients.http_client import init_http_client, close_http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("服务启动中...")
    init_dialogue_engine()
    init_db_engine()
    init_http_client()
    print("服务启动成功")
    yield
    print("服务关闭中...")
    await close_db_engine()
    await close_http_client()
    print("服务关闭成功")



# 创建fastapi实例
app = FastAPI(lifespan=lifespan)

# 挂载路由对象
app.include_router(chat_router)