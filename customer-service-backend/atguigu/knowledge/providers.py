import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from atguigu.clients import finance_client
from atguigu.domain.message import UserMessage
from atguigu.domain.state import DialogueState


@dataclass
class KnowledgeChunk:
    content: str


class KnowledgeProvider(ABC):
    provider_id = ""

    @abstractmethod
    async def retrieve(
            self,
            state: DialogueState,
            user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        pass


class FinanceLoanProductProvider(KnowledgeProvider):
    """贷款产品信息：列表 + 详情（利率/期限/额度/准入规则）"""
    provider_id = "api.finance.loan"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        # 优先使用聚焦对象（前端点选的产品）
        product_code = None
        focused = state.shared.focused_object
        if focused is not None and focused.type == "loan":
            product_code = focused.id

        if product_code:
            detail = await finance_client.get_loan_product(product_code)
            chunks = [KnowledgeChunk(content=f"贷款产品信息:\n{json.dumps(detail, ensure_ascii=False, indent=2)}")]
            return chunks

        # 无聚焦对象：返回可售贷款产品列表
        products = await finance_client.list_loan_products()
        text = json.dumps(products, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"可售贷款产品列表:\n{text}")]


class FinanceWealthProductProvider(KnowledgeProvider):
    """理财产品信息：列表 + 详情（收益率/风险/起购金额）"""
    provider_id = "api.finance.wealth"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        product_code = None
        focused = state.shared.focused_object
        if focused is not None and focused.type == "wealth":
            product_code = focused.id

        if product_code:
            detail = await finance_client.get_wealth_product(product_code)
            return [KnowledgeChunk(content=f"理财产品信息:\n{json.dumps(detail, ensure_ascii=False, indent=2)}")]

        products = await finance_client.list_wealth_products()
        text = json.dumps(products, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"可售理财产品列表:\n{text}")]


class FinanceAccountInfoProvider(KnowledgeProvider):
    """账户/存款产品信息（客户账户列表）"""
    provider_id = "api.finance.account"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        customer_no = None
        focused = state.shared.focused_object
        if focused is not None and focused.type == "account":
            customer_no = focused.attributes.get("customer_no") or focused.id

        if not customer_no:
            # 尝试从对话历史/上下文取客户号：这里简化，无则提示
            return [KnowledgeChunk(content="请提供客户号后查询账户信息。")]

        accounts = await finance_client.list_accounts(customer_no)
        text = json.dumps(accounts, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"客户 {customer_no} 账户信息:\n{text}")]


class FinanceFAQProvider(KnowledgeProvider):
    """金融 FAQ 检索：基于关键词匹配 FAQ 语料"""
    provider_id = "faq.finance"

    # 关键词分组 → FAQ 条目
    _FAQ = [
        {
            "keywords": ["存款", "活期", "定期", "利率", "利息", "存期"],
            "content": (
                "中州银行存款产品利率参考：活期存款利率按央行基准执行；定期存款（整存整取）利率随存期递增，"
                "具体以当日我行挂牌利率为准，可通过网点或手机银行查询。"
            ),
        },
        {
            "keywords": ["贷款", "利率", "定价", "利息", "按揭", "消费贷", "经营贷"],
            "content": (
                "贷款定价按产品与客户资质确定，参考利率区间为产品基准利率；"
                "实际利率与征信评分、贷款金额和期限相关，最终以审批结果为准。"
            ),
        },
        {
            "keywords": ["理财", "业绩", "基准", "收益率", "回报", "预期"],
            "content": (
                "理财产品业绩比较基准是产品管理运作的目标参考，不代表实际收益承诺。"
                "实际收益以产品到期/赎回时净值为准，理财非存款、产品有风险、投资须谨慎。"
            ),
        },
        {
            "keywords": ["手续费", "转账", "取现", "账户管理", "年费", "跨行"],
            "content": (
                "中州银行手续费规则：同行/跨行转账按渠道与金额收取不同标准，柜面/网银/手机银行各有优惠；"
                "借记卡一般不收取账户管理费；信用卡年费按卡种收取，金卡、白金卡权益不同。"
            ),
        },
        {
            "keywords": ["提前还款", "违约金", "提前", "还款"],
            "content": (
                "贷款支持提前还款，需提前申请并按合同约定支付相应费用；"
                "部分产品提前还款无违约金，具体以贷款合同条款为准。"
            ),
        },
        {
            "keywords": ["信用卡", "还款", "账单日", "还款日", "免息", "最低还款", "逾期"],
            "content": (
                "信用卡还款规则：按账单日生成账单，还款日一般为账单日后第25天；"
                "账单日与还款日之间为免息期，最长约50天；"
                "可按最低还款额还款，未还部分计收利息；逾期将产生罚息并影响征信。"
            ),
        },
        {
            "keywords": ["风险", "保本", "亏损", "适当性", "测评", "风险等级"],
            "content": (
                "金融产品风险提示：理财产品不保本、不保息，收益随市场波动，可能出现本金亏损；"
                "购买前请完成风险测评，选择与自身风险承受能力匹配的产品。"
            ),
        },
        {
            "keywords": ["金卡", "白金卡", "信用卡", "额度", "权益", "年费"],
            "content": (
                "信用卡金卡与白金卡区别：白金卡信用额度更高（通常5万起）、权益更丰富（机场贵宾厅、高额保险等），"
                "年费也相应更高；金卡额度适中、年费较低。具体以卡片申请页面为准。"
            ),
        },
        {
            "keywords": ["客服", "人工", "坐席", "联系", "电话"],
            "content": "如需人工帮助，可以转接中州银行人工坐席，或拨打我行客服热线。",
        },
    ]

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        text = user_message.text or ""
        if not text:
            return [KnowledgeChunk(content="未检索到相关问题")]

        matched = []
        for faq in self._FAQ:
            if any(keyword in text for keyword in faq["keywords"]):
                matched.append(faq["content"])

        if not matched:
            return [KnowledgeChunk(content="未检索到相关问题，请换个问法，或转接人工客服。")]

        content = "FAQ 相关知识：\n" + "\n\n".join(matched)
        return [KnowledgeChunk(content=content)]
