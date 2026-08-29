from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.clients import database
from atguigu.engine.builder import build_dialogue_engine
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.repository.dialogue_state_repository import DialogueStateRepository
from atguigu.service.dialogue_service import DialogueService



_dialogue_engine: DialogueEngine | None = None

def get_engine() -> DialogueEngine:
    return _dialogue_engine

def init_dialogue_engine() -> None:
    global _dialogue_engine
    _dialogue_engine = build_dialogue_engine()


async def get_session():
    # 注意：此处要引入database，而不是session_factory，否则会引入None值
    async with database.session_factory() as session:
        # 执行到 yield 时，session 对象被交给当前的请求使用
        # 请求处理结束后，FastAPI会继续执行生成器并退出 async with，当前session对象随之关闭
        yield session

async def get_repository(session: AsyncSession = Depends(get_session)) -> DialogueStateRepository:
    return DialogueStateRepository(session)

async def get_dialogue_service(
        engine: DialogueEngine = Depends(get_engine),
        repository: DialogueStateRepository = Depends(get_repository)) -> DialogueService:

    return DialogueService(
        dialogue_state_repository = repository,
        dialogue_engine=engine
    )