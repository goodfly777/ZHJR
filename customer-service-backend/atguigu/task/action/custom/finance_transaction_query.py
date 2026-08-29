import datetime
import re
from typing import Any

from atguigu.clients import finance_client
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult

# 交易类型中文映射（finance 枚举）
_TRANSACTION_TYPE_LABEL = {
    "transfer": "转账",
    "consume": "消费",
    "deposit": "存款",
    "withdraw": "取现",
    "refund": "退款",
    "adjustment": "调账",
    "loan_disbursement": "放款",
    "loan_repayment": "还款",
    "wealth_purchase": "理财申购",
    "wealth_redeem": "理财赎回",
}


def _resolve_trade_date(text: str) -> str | None:
    """将自然语言日期解析为 YYYY-MM-DD，无法解析返回 None。

    支持：今天/昨天/前天/具体日期 YYYY-MM-DD 或 YYYY年MM月DD日。
    """
    if not text:
        return None
    s = str(text).strip()
    today = datetime.date.today()
    if "今天" in s:
        return today.isoformat()
    if "昨天" in s:
        return (today - datetime.timedelta(days=1)).isoformat()
    if "前天" in s:
        return (today - datetime.timedelta(days=2)).isoformat()
    # YYYY-MM-DD
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s)
    if m:
        try:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except ValueError:
            return None
    return None


class FinanceTransactionQueryAction(Action):

    name = "action_finance_transaction_query"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:

        slots = state.tasks.active.slots
        account_no = slots.get("account_no")

        if not account_no:
            return ActionResult(slot_updates={"transaction_summary": "未能识别账户号，请重新提供。"})

        params: dict[str, Any] = {"page_no": 1, "page_size": 10}
        trade_date = _resolve_trade_date(slots.get("trade_date"))
        if trade_date:
            params["start_time"] = f"{trade_date}T00:00:00"
            params["end_time"] = f"{trade_date}T23:59:59"

        result = await finance_client.list_transactions(account_no, params)
        items = result.get("list") or []

        if not items:
            return ActionResult(slot_updates={
                "transaction_summary": f"账户 {account_no} 在查询条件下暂无交易记录。"
            })

        lines = []
        for txn in items[:10]:
            txn_type = _TRANSACTION_TYPE_LABEL.get(txn.get("transaction_type"), txn.get("transaction_type"))
            lines.append(
                f"- {txn.get('transaction_no')}｜{txn.get('transaction_at', '')}｜{txn_type}"
                f"｜{txn.get('transaction_amount')}元｜"
                f"{txn.get('counterparty_name') or txn.get('merchant_name') or '--'}"
            )

        total = result.get("total_count")
        summary = f"账户 {account_no} 共查到 {total or len(items)} 条交易（以下为前 {len(items)} 条）：\n" + "\n".join(lines)
        if total and int(total) > len(items):
            summary += f"\n更多记录可通过人工客服或柜台查询。"
        return ActionResult(slot_updates={"transaction_summary": summary})
