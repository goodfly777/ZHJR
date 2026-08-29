
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from atguigu.conf.config import settings

"""
三要素：
1、引擎 engine
2、session工厂 session_factory: 通过sessionmaker创建
3、session对象：通过session工厂创建
"""

# 声明全局变量
engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None

# 初始化资源
def init_db_engine():
    global engine, session_factory

    # 1. 创建异步引擎
    engine = create_async_engine(
        settings.database_url,
        # SQL 日志打印开关，False关闭，True开启。开发时开启，生产时关闭
        echo=True,

        # 默认值False
        # 当设置成 True 时：
        # 每次从数据库连接池中取出连接前，先执行一条SQL语句（SELECT 1，连接探测），探测连接对象是否存活
        # 如果连接已断开，则丢弃这个连接，尝试获取新连接
        pool_pre_ping=True,
        pool_size=5,  # 数据库连接池中的常规连接数
        max_overflow=10,  # 数据库连接池中最大连接数
        pool_recycle=180,  # 数据库连接池中连接的回收时间，单位为秒
    )

    # 2. 创建异步session工厂
    # expire_on_commit=False: TODO
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

# 释放资源
async def close_db_engine():
    global engine, session_factory

    # 释放数据库引擎和session工厂资源
    if engine is not None:

        # 关闭连接池，释放资源，但是对象本身还活着
        await engine.dispose()
    engine = None
    session_factory = None

if __name__ == '__main__':

    async def test():

        # 初始化引擎和工厂（应用程序启动的时候调用这句话）
        init_db_engine()

        async with session_factory() as session:
            # execute 接收一个SQL对象
            result = await session.execute(text("SELECT 1"))
            data = result.fetchone()
            print(data)
            print(type(data))

            # 显示提交
            await session.commit()

        # 关闭引擎，销毁引擎和工厂（应用程序停止的时候调用这句话）
        await close_db_engine()


    import asyncio
    asyncio.run(test())
