"""金融业务 API（finance-data）客户端封装。

- 统一拼接 BaseURL + /api/v1 前缀
- GET 走带超时/重试的 finance_get（只读接口）
- POST 写接口必须带 request_no（幂等键），由调用方生成并复用（存会话槽位）
- 响应统一 {code, message, request_id, data}，code=0 成功；金额均为字符串，透传不做浮点运算
"""

import logging
import uuid

from atguigu.clients import http_client
from atguigu.clients.http_client import finance_get
from atguigu.conf.config import settings

logger = logging.getLogger(__name__)


def finance_url(path: str) -> str:
    """拼接 finance API 完整 URL，path 形如 /customers/{customer_no}/accounts"""
    return f"{settings.finance_api_base_url}{settings.finance_api_prefix}{path}"


def generate_request_no(business_type: str) -> str:
    """生成一次业务办理的幂等 request_no，同一业务实例内应复用（由 Action 存入槽位）"""
    return f"{business_type}-{uuid.uuid4().hex[:24]}"


async def finance_post(path: str, body: dict) -> dict:
    """调用 finance 写接口（带 request_no），失败返回 {} 不抛异常。

    注意：写接口不做自动重试（幂等语义由 request_no 保证，重试交给上层按会话语义决策）。
    """
    if http_client.http_client is None:
        return {}
    try:
        response = await http_client.http_client.post(finance_url(path), json=body)
        payload = response.json()
        if payload.get("code") not in (0, "0"):
            logger.warning("finance POST %s 业务失败: %s %s", path, payload.get("code"), payload.get("message"))
            return {}
        return payload.get("data") or {}
    except Exception as exc:  # noqa: BLE001 网络/超时/解析错误
        logger.warning("finance POST %s 调用异常: %s", path, exc)
        return {}


# ---- 领域方法：查询 ----

async def get_customer(customer_no: str) -> dict:
    return await finance_get(finance_url(f"/customers/{customer_no}"))


async def list_accounts(customer_no: str) -> dict:
    return await finance_get(finance_url(f"/customers/{customer_no}/accounts"))


async def get_account(account_no: str) -> dict:
    return await finance_get(finance_url(f"/accounts/{account_no}"))


async def list_transactions(account_no: str, params: dict | None = None) -> dict:
    return await finance_get(finance_url(f"/accounts/{account_no}/transactions"), params=params or {})


async def get_transaction(transaction_no: str) -> dict:
    return await finance_get(finance_url(f"/transactions/{transaction_no}"))


async def list_loan_products() -> dict:
    return await finance_get(finance_url("/loan/products"))


async def get_loan_product(product_code: str) -> dict:
    return await finance_get(finance_url(f"/loan/products/{product_code}"))


async def list_credit_limits(customer_no: str) -> dict:
    return await finance_get(finance_url(f"/customers/{customer_no}/credit-limits"))


async def list_wealth_products() -> dict:
    return await finance_get(finance_url("/wealth/products"))


async def get_wealth_product(product_code: str) -> dict:
    return await finance_get(finance_url(f"/wealth/products/{product_code}"))


async def list_wealth_positions(customer_no: str) -> dict:
    return await finance_get(finance_url(f"/customers/{customer_no}/wealth/positions"))


# ---- 领域方法：写操作 ----

async def create_loan_application(request_no: str, body: dict) -> dict:
    return await finance_post("/loan/applications", {"request_no": request_no, **body})


async def create_credit_application(request_no: str, body: dict) -> dict:
    return await finance_post("/credit/applications", {"request_no": request_no, **body})


async def create_support_ticket(request_no: str, body: dict) -> dict:
    return await finance_post("/support/tickets", {"request_no": request_no, **body})
