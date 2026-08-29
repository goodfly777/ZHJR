import asyncio
import logging

from httpx import AsyncClient, Timeout

from atguigu.conf.config import settings

logger = logging.getLogger(__name__)

# 声明全局变量
http_client: AsyncClient | None = None

# 金融业务 API 默认鉴权请求头（Bearer 员工号 + 渠道码），所有 finance 请求自动携带
DEFAULT_FINANCE_HEADERS = {
    "Authorization": f"Bearer {settings.finance_bearer_token}",
    "X-Channel-Code": settings.finance_channel_code,
}


# 初始化http客户端
def init_http_client():
    global http_client
    # 注入金融鉴权头与超时（连接/读/写）
    http_client = AsyncClient(
        headers=DEFAULT_FINANCE_HEADERS,
        timeout=Timeout(settings.finance_timeout_seconds),
    )


# 关闭http客户端
async def close_http_client():
    if http_client is not None:
        await http_client.aclose()


async def finance_get(url: str, **kwargs) -> dict:
    """带超时与重试的 GET 请求封装（finance API 只读接口）。

    失败（网络/超时/5xx/非 code=0）时返回空 dict 并记录告警，不抛异常，
    保证单次对话失败不影响整体服务（对应非功能需求 6.1 可靠性）。
    """
    if http_client is None:
        logger.error("http_client 未初始化")
        return {}

    max_retries = settings.finance_max_retries
    backoff = settings.finance_retry_backoff_seconds

    for attempt in range(max_retries + 1):
        try:
            response = await http_client.get(url, **kwargs)
            if response.status_code >= 500:
                # 5xx 可重试
                if attempt < max_retries:
                    await asyncio.sleep(backoff * (attempt + 1))
                    continue
                logger.warning("finance API %s 返回 %s", url, response.status_code)
                return {}
            payload = response.json()
            if payload.get("code") not in (0, "0"):
                logger.warning("finance API %s 业务失败: %s %s",
                               url, payload.get("code"), payload.get("message"))
                return {}
            return payload.get("data") or {}
        except Exception as exc:  # noqa: BLE001 网络错误/超时/解析错误
            if attempt < max_retries:
                await asyncio.sleep(backoff * (attempt + 1))
                continue
            logger.warning("finance API %s 调用异常: %s", url, exc)
            return {}

    return {}


if __name__ == '__main__':
    init_http_client()

    async def test():
        print("http_client 初始化成功")

        await close_http_client()

    import asyncio
    asyncio.run(test())
