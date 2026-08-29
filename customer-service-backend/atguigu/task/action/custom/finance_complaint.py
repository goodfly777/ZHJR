from typing import Any

from atguigu.clients import finance_client
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult

# 工单类型中文映射（finance 枚举 + 常用分类）
_TICKET_TYPE_LABEL = {
    "account_issue": "账户问题",
    "transaction_issue": "交易问题",
    "wealth_issue": "理财问题",
    "loan_issue": "贷款问题",
    "repayment_issue": "还款问题",
    "complaint": "投诉",
    "other": "其他",
}


class FinanceComplaintAction(Action):

    name = "action_finance_complaint"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:

        slots = state.tasks.active.slots
        customer_no = slots.get("customer_no")
        description = slots.get("complaint_description")
        ticket_type = slots.get("ticket_type") or "complaint"
        related_txn_no = slots.get("related_txn_no")

        if not customer_no or not description:
            return ActionResult(slot_updates={
                "complaint_result": "工单信息不完整（问题描述必填），请补充后再提交。"
            })

        # 幂等 request_no
        request_no = slots.get("finance_request_no") or finance_client.generate_request_no("COMPLAINT")
        slots["finance_request_no"] = request_no

        content = f"客户投诉：{description}"
        if related_txn_no:
            content += f"（关联交易号：{related_txn_no}）"

        body = {
            "customer_no": customer_no,
            "ticket_type": ticket_type,
            "ticket_title": "客户投诉工单",
            "ticket_content": content,
            "related_type": "none",
            "related_id": None,
        }
        result = await finance_client.create_support_ticket(request_no, body)

        if not result:
            return ActionResult(slot_updates={
                "complaint_result": "工单提交失败，请稍后重试或联系人工客服。"
            })

        ticket_no = result.get("ticket_no")
        return ActionResult(slot_updates={
            "complaint_result": (
                f"您的投诉工单已创建成功，工单号：{ticket_no}。"
                f"我们将在 1 个工作日内核实处理，处理结果会通过您预留的联系方式反馈。"
            )
        })
