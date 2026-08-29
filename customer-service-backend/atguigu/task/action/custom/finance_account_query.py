from typing import Any

from atguigu.clients import finance_client
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult


class FinanceAccountQueryAction(Action):

    name = "action_finance_account_query"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:

        slots = state.tasks.active.slots
        customer_no = slots.get("customer_no")
        account_no = slots.get("account_no")

        if not customer_no:
            return ActionResult(slot_updates={"account_summary": "未能识别客户号，请重新提供。"})

        # 1. 查客户档案，校验状态（closed/cancelled/blacklisted 等不可办理）
        customer = await finance_client.get_customer(customer_no)
        profile = customer.get("customer_profile") or {}
        status = customer.get("customer_status") or profile.get("customer_status") or ""
        if status in ("closed", "cancelled", "blacklisted"):
            return ActionResult(slot_updates={
                "account_summary": f"客户 {customer_no} 当前状态为 {status}，无法办理账户查询，请联系人工客服。"
            })

        # 2. 客户账户列表
        accounts = await finance_client.list_accounts(customer_no)
        account_list = accounts.get("list") or []

        # 3. 若未指定账户，则返回账户列表供选择
        if not account_no:
            if not account_list:
                return ActionResult(slot_updates={"account_summary": "该客户名下暂无可查询的账户。"})
            lines = []
            for acc in account_list:
                product = acc.get("account_product") or {}
                lines.append(
                    f"- {acc.get('account_no')}（{product.get('product_name') or acc.get('currency_code')}）"
                    f" 余额：{acc.get('balance_amount')}元"
                )
            return ActionResult(slot_updates={
                "account_summary": "该客户名下账户如下，请选择账户号以查看详情：\n" + "\n".join(lines)
            })

        # 4. 指定账户：查账户详情（余额/冻结/可用）
        detail = await finance_client.get_account(account_no)
        if not detail:
            return ActionResult(slot_updates={
                "account_summary": f"账户 {account_no} 查询失败，请核对账户号后重试。"
            })
        product = detail.get("account_product") or {}
        balance = detail.get("balance_amount")
        frozen = detail.get("frozen_amount")
        # finance 详情未直接返回可用余额；按需求口径：可用余额 = 余额 - 冻结（金额为字符串，仅展示原样）
        available = f"{float(balance or 0) - float(frozen or 0):.2f}" if (balance or frozen) else None

        summary = (
            f"账户 {account_no} 当前状态：{detail.get('account_status')}；"
            f"产品：{product.get('product_name')}；"
            f"账户余额：{balance}元；冻结金额：{frozen}元；可用余额：约{available}元。"
        )
        return ActionResult(slot_updates={"account_summary": summary})
