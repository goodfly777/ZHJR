from typing import Any

from atguigu.clients import finance_client
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult

# 贷款类型中文映射
_LOAN_TYPE_LABEL = {
    "consumer": "消费贷",
    "cash": "现金贷",
    "installment": "分期贷",
    "business": "经营贷",
}


def _parse_amount(text: str) -> str | None:
    """将用户输入的中文/数字金额统一转换为数字字符串。

    支持：'5万'、'50000'、'10 万元'、'5,0000' 等。
    无法解析时返回 None。
    """
    if not text:
        return None
    s = str(text).strip().replace(",", "").replace("，", "").replace("元", "").replace("块", "")
    multiplier = 1.0
    if "万" in s:
        multiplier = 10000.0
        s = s.replace("万", "")
    elif "千" in s:
        multiplier = 1000.0
        s = s.replace("千", "")
    try:
        value = float(s)
    except (TypeError, ValueError):
        return None
    return f"{value * multiplier:.0f}"


class FinanceLoanApplyAction(Action):

    name = "action_finance_loan_apply"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:

        slots = state.tasks.active.slots
        customer_no = slots.get("customer_no")

        if not customer_no:
            return ActionResult(slot_updates={"loan_result": "未能识别客户号，请重新提供。"})

        # 1. 查询客户授信额度
        limits = await finance_client.list_credit_limits(customer_no)
        limit_list = limits.get("list") or []
        active_limit = next((x for x in limit_list if x.get("limit_no")), None)

        if not active_limit:
            # 无授信额度 → 引导走授信申请分支（流程配置里处理，这里给出提示）
            return ActionResult(slot_updates={
                "loan_result": "您当前没有可用授信额度，请先申请授信额度后再办理贷款。",
                "loan_needs_credit": "yes",
            })

        # 2. 组装申请参数（金额/期限统一为数字）
        apply_amount = _parse_amount(slots.get("apply_amount"))
        apply_term = slots.get("apply_term_months")

        if not apply_amount or not apply_term:
            return ActionResult(slot_updates={
                "loan_result": "贷款金额或期限格式有误，请重新输入（如金额 5万、期限 12个月）。"
            })
        try:
            apply_term_months = int(str(apply_term).replace("个月", "").replace("年", ""))
            if "年" in str(slots.get("apply_term_months")):
                apply_term_months *= 12
        except (TypeError, ValueError):
            return ActionResult(slot_updates={"loan_result": "贷款期限格式有误，请用月数输入，如 12。"})

        # 3. 准入预检：查授信额度对应产品的金额/期限范围
        limit_no = active_limit.get("limit_no")
        available = active_limit.get("available_limit_amount")
        product_code = active_limit.get("product_code")
        product_detail = (await finance_client.get_loan_product(product_code)).get("product_detail", {}) if product_code else {}

        def _fmt_amt(v: str) -> str:
            try:
                return f"{float(v):.0f}" if float(v) == int(float(v)) else str(float(v))
            except (TypeError, ValueError):
                return str(v)

        min_amount, max_amount = product_detail.get("min_amount"), product_detail.get("max_amount")
        min_term, max_term = product_detail.get("min_term_months"), product_detail.get("max_term_months")
        product_name = product_detail.get("product_name") or product_code

        if min_amount and float(apply_amount) < float(min_amount):
            return ActionResult(slot_updates={
                "loan_result": f"{product_name} 最低可贷 {_fmt_amt(min_amount)} 元，请调整贷款金额。"
            })
        if max_amount and float(apply_amount) > float(max_amount):
            return ActionResult(slot_updates={
                "loan_result": f"{product_name} 最高可贷 {_fmt_amt(max_amount)} 元，请调整贷款金额。"
            })
        if min_term and apply_term_months < int(min_term):
            return ActionResult(slot_updates={
                "loan_result": f"{product_name} 最短期限为 {min_term} 个月，请调整贷款期限。"
            })
        if max_term and apply_term_months > int(max_term):
            return ActionResult(slot_updates={
                "loan_result": f"{product_name} 最长期限为 {max_term} 个月，请调整贷款期限。"
            })
        try:
            if float(apply_amount) > float(available or 0):
                return ActionResult(slot_updates={
                    "loan_result": f"申请金额超出可用授信额度（可用 {available}元），请调整金额或先提升额度。"
                })
        except (TypeError, ValueError):
            return ActionResult(slot_updates={"loan_result": "贷款金额格式有误，请重新输入。"})

        # 4. 幂等 request_no：同一业务实例内复用（存槽位）
        request_no = slots.get("finance_request_no") or finance_client.generate_request_no("LOAN")
        slots["finance_request_no"] = request_no

        # 5. 提交贷款申请
        body = {
            "customer_no": customer_no,
            "limit_no": limit_no,
            "apply_amount": apply_amount,
            "apply_term_months": apply_term_months,
            "repayment_method": slots.get("repayment_method") or "equal_principal_interest",
            "loan_purpose": slots.get("loan_purpose") or "consume",
            "materials": [],
        }
        result = await finance_client.create_loan_application(request_no, body)

        if not result:
            return ActionResult(slot_updates={
                "loan_result": "贷款申请提交失败，请稍后重试或联系人工客服。"
            })

        app_no = result.get("application_no")
        status = result.get("application_status") or "submitted"
        return ActionResult(slot_updates={
            "loan_result": (
                f"您的贷款申请已提交成功。申请编号：{app_no}，"
                f"当前状态：{status}。请耐心等待人工审批，审批结果以我行通知为准。"
            )
        })
