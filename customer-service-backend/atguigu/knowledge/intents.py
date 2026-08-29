from dataclasses import dataclass, field


@dataclass
class KnowledgeIntent:
    id: str
    description: str
    provider_ids: list[str] = field(default_factory=list)
    requires_object: str | None = None

KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {

    "loan_product_info": KnowledgeIntent(
        id="loan_product_info",
        description="贷款产品信息咨询（利率、期限、额度、准入条件）",
        provider_ids=["api.finance.loan"],
    ),

    "wealth_product_info": KnowledgeIntent(
        id="wealth_product_info",
        description="理财产品信息咨询（收益率、风险等级、起购金额）",
        provider_ids=["api.finance.wealth"],
    ),

    "account_info": KnowledgeIntent(
        id="account_info",
        description="账户/存款产品信息咨询（账户类型、存款利率、起存金额）",
        provider_ids=["api.finance.account", "faq.finance"],
    ),

    "faq_rate": KnowledgeIntent(
        id="faq_rate",
        description="利率说明咨询（活期/定期存款利率、贷款定价、理财业绩基准、基金费率）",
        provider_ids=["faq.finance"],
    ),

    "faq_fee": KnowledgeIntent(
        id="faq_fee",
        description="手续费规则咨询（转账手续费、取现费、账户管理费、卡年费）",
        provider_ids=["faq.finance"],
    ),

    "faq_prepay": KnowledgeIntent(
        id="faq_prepay",
        description="提前还款政策咨询（是否支持提前还款、违约金、次数限制）",
        provider_ids=["faq.finance"],
    ),

    "faq_creditcard_repay": KnowledgeIntent(
        id="faq_creditcard_repay",
        description="信用卡还款规则咨询（账单日、还款日、免息期、最低还款、逾期罚息）",
        provider_ids=["faq.finance"],
    ),

    "faq_risk": KnowledgeIntent(
        id="faq_risk",
        description="金融风险提示咨询（理财非保本、适当性、投资风险）",
        provider_ids=["faq.finance"],
    ),

    "general_finance_info": KnowledgeIntent(
        id="general_finance_info",
        description="金融通用信息咨询（产品介绍、使用指南、金融政策）",
        provider_ids=["faq.finance"],
    ),
}
