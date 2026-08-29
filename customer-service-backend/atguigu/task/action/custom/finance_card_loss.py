from typing import Any

from atguigu.clients import finance_client
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult


def mask_card_no(card_no: str) -> str:
    """卡号脱敏：仅保留末 4 位"""
    if not card_no:
        return ""
    if len(card_no) <= 4:
        return "*" * len(card_no)
    return "*" * (len(card_no) - 4) + card_no[-4:]


class FinanceCardLossAction(Action):

    name = "action_finance_card_loss"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:

        slots = state.tasks.active.slots
        customer_no = slots.get("customer_no")
        card_no = slots.get("card_no")
        loss_reason = slots.get("loss_reason")
        identity_check = slots.get("identity_check")

        if not all([customer_no, card_no, loss_reason]):
            return ActionResult(slot_updates={
                "card_loss_result": "挂失信息不完整（卡号/挂失原因），请补充后再提交。"
            })

        # 幂等 request_no
        request_no = slots.get("finance_request_no") or finance_client.generate_request_no("CARD_LOSS")
        slots["finance_request_no"] = request_no

        # 信用卡挂失无专用 API → 落为客服工单（ticket_type=account_issue），转人工处理
        masked = mask_card_no(card_no)
        content = (
            f"信用卡挂失受理：客户 {customer_no}，卡号 {masked}，"
            f"挂失原因：{loss_reason}，身份验证：{identity_check or '未提供'}。请人工跟进补卡/资金冻结。"
        )
        body = {
            "customer_no": customer_no,
            "ticket_type": "account_issue",
            "ticket_title": "信用卡挂失受理",
            "ticket_content": content,
            "related_type": "none",
            "related_id": None,
        }
        result = await finance_client.create_support_ticket(request_no, body)

        if not result:
            return ActionResult(slot_updates={
                "card_loss_result": "挂失申请提交失败，请稍后重试，或立即致电人工客服冻结卡片。"
            })

        ticket_no = result.get("ticket_no")
        return ActionResult(slot_updates={
            "card_loss_result": (
                f"您的信用卡挂失申请已受理，工单号：{ticket_no}。"
                f"我们将尽快转人工为您补办卡片/冻结资金，请保持联系方式畅通。"
            )
        })
