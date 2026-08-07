import re
from decimal import Decimal

from app.agents.types import CompletenessResult, ExtractionResult, IntentResult, KnowledgeResult, ReportResult, RiskResult


class MockAnalysisProvider:
    """押金纠纷 V1 的确定性规则基线。

    该 Provider 用于演示产品流程和建立可复现评测基线，不代表真实大模型、
    向量 RAG 或法律意见。
    """

    provider_name = "mock"
    model_name = "rules-baseline"
    prompt_version = "mock-v1.2"
    knowledge_version = "civil-code-cn-2020-v1"

    KNOWLEDGE_BASE = [
        {
            "id": "civil-code-710",
            "title": "《中华人民共和国民法典》第七百一十条",
            "content": "承租人按照约定的方法或者根据租赁物的性质使用租赁物，致使租赁物受到损耗的，不承担赔偿责任。",
            "source_url": "https://www.gov.cn/xinwen/2020-06/01/content_5516649.htm",
            "effective_date": "2021-01-01",
            "jurisdiction": "中国大陆",
            "tags": ["DEPOSIT", "押金", "扣款", "损耗", "损坏"],
        },
        {
            "id": "civil-code-733",
            "title": "《中华人民共和国民法典》第七百三十三条",
            "content": "租赁期限届满，承租人应当返还租赁物。返还的租赁物应当符合按照约定或者根据租赁物的性质使用后的状态。",
            "source_url": "https://www.gov.cn/xinwen/2020-06/01/content_5516649.htm",
            "effective_date": "2021-01-01",
            "jurisdiction": "中国大陆",
            "tags": ["DEPOSIT", "押金", "退租", "到期", "交接"],
        },
    ]

    OUT_OF_SCOPE_RULES = [
        ("REPAIR", "维修责任纠纷", ["漏水", "热水器", "空调坏", "维修责任", "报修"]),
        ("RENT_CANCEL", "提前退租纠纷", ["提前退租", "提前搬走", "解约", "违约金"]),
        ("CONTRACT", "合同风险检测", ["审合同", "合同条款", "霸王条款", "签合同前"]),
    ]

    def identify_intent(self, description: str, fallback_type: str = "DEPOSIT") -> IntentResult:
        for case_type, label, keywords in self.OUT_OF_SCOPE_RULES:
            if any(keyword in description for keyword in keywords):
                return IntentResult(case_type, label, 0.95, False)

        deposit_keywords = ["押金", "保证金", "不退", "扣押金", "押一付", "退房扣款"]
        fee_deduction = any(role in description for role in ("房东", "中介", "二房东")) and "扣" in description and any(
            fee in description for fee in ("清洁费", "维修费")
        )
        if any(keyword in description for keyword in deposit_keywords) or fee_deduction:
            return IntentResult("DEPOSIT", "押金返还纠纷", 0.93, True)

        if fallback_type == "DEPOSIT":
            return IntentResult("UNKNOWN", "信息不足，暂无法确认是否为押金纠纷", 0.45, False)
        return IntentResult("OUT_OF_SCOPE", "当前版本暂不支持该问题", 0.6, False)

    def extract_information(self, description: str, amount: Decimal | None) -> ExtractionResult:
        date_matches = re.findall(r"\d{4}[年\-/]\d{1,2}(?:[月\-/]\d{1,2}[日号]?)?", description)
        amount_match = re.search(r"(?:还欠|仍欠|未退|不退|扣(?:除)?)(\d+(?:\.\d{1,2})?)\s*(?:元|块)", description)
        if amount_match is None:
            amount_match = re.search(r"(\d+(?:\.\d{1,2})?)\s*(?:元|块)", description)
        parsed_amount = f"{amount_match.group(1)}元" if amount_match else None
        if parsed_amount is None:
            chinese_thousand = re.search(r"([一二三四五六七八九])千\s*元?", description)
            if chinese_thousand:
                digit = "一二三四五六七八九".index(chinese_thousand.group(1)) + 1
                parsed_amount = f"{digit * 1000}元"
        if parsed_amount is None and amount is not None:
            parsed_amount = f"{amount}元"

        roles = [role for role in ("房东", "中介", "二房东") if role in description]
        if roles and any(pronoun in description for pronoun in ("我", "本人", "租客")):
            roles.insert(0, "租客")

        disputes = [keyword for keyword in ("押金", "保证金", "扣款", "维修费", "清洁费", "退租") if keyword in description]

        if any(keyword in description for keyword in ("已经到期", "合同到期", "租期届满", "到期退房", "正常退租")):
            lease_status = "EXPIRED"
        elif any(keyword in description for keyword in ("尚未到期", "没到期", "提前退租", "提前搬")):
            lease_status = "ONGOING"
        else:
            lease_status = "UNKNOWN"

        if any(negative in description for negative in ("没有说明原因", "没有说原因", "未说明原因", "没说原因")):
            deduction_reason = None
        else:
            reason_match = re.search(r"(?:理由是|原因是)([^，。；]{2,40})(?:，|。|；|$)", description)
            if reason_match is None:
                reason_match = re.search(r"(?:房东|中介)?(?:说|称|以)([^，。；]{2,40}?)(?:为由|所以|，|。|；|$)", description)
            deduction_reason = reason_match.group(1).strip() if reason_match else None
        if deduction_reason is None:
            known_reasons = [reason for reason in ("墙面损坏", "房屋损坏", "卫生不合格", "清洁费", "维修费", "违约") if reason in description]
            deduction_reason = "、".join(known_reasons) if known_reasons else None

        lease_period = " 至 ".join(date_matches[:2]) if len(date_matches) >= 2 else (date_matches[0] if date_matches else None)
        return ExtractionResult(lease_period, parsed_amount, roles, disputes, lease_status, deduction_reason)

    def assess_completeness(self, extracted: ExtractionResult) -> CompletenessResult:
        checks = [
            (extracted.amount, "涉及金额", "被扣或未退还的押金具体是多少元？", 0.25, True),
            (extracted.roles, "争议对象", "扣留押金的是房东、中介还是二房东？", 0.15, True),
            (extracted.deduction_reason, "扣款理由", "对方给出的扣款或拒退理由是什么？", 0.25, True),
            (extracted.lease_status != "UNKNOWN", "租约状态", "租赁合同是否已经到期，还是属于提前退租？", 0.20, True),
            (extracted.lease_period, "租赁时间", "租赁合同约定的起止日期分别是什么？", 0.10, False),
            (extracted.disputes, "具体争议点", "双方目前对哪一笔费用或哪项房屋状况存在争议？", 0.05, False),
        ]

        missing = [field for value, field, _, _, _ in checks if not value]
        questions = [question for value, _, question, _, _ in checks if not value]
        score = round(sum(weight for value, _, _, weight, _ in checks if value), 2)
        core_fields_complete = all(bool(value) for value, _, _, _, core in checks if core)
        return CompletenessResult(core_fields_complete and score >= 0.8, score, core_fields_complete, missing, questions[:3])

    def retrieve_knowledge(self, intent: IntentResult, description: str) -> KnowledgeResult:
        if not intent.in_scope:
            return KnowledgeResult([], self.knowledge_version)

        query = f"{intent.case_type} {description}".lower()
        scored = [(sum(tag.lower() in query for tag in document["tags"]), document) for document in self.KNOWLEDGE_BASE]
        documents = [document for score, document in sorted(scored, key=lambda item: item[0], reverse=True) if score]
        references = [
            {key: value for key, value in item.items() if key != "tags"}
            for item in (documents[:2] or self.KNOWLEDGE_BASE)
        ]
        return KnowledgeResult(references, self.knowledge_version)

    def analyze_risk(self, completeness: CompletenessResult, evidence_count: int) -> RiskResult:
        if not completeness.core_fields_complete:
            return RiskResult("HIGH", "核心事实仍不完整，当前无法形成可靠判断，应先补齐金额、扣款理由和租约状态。")
        if evidence_count == 0:
            return RiskResult("MEDIUM", "核心事实已基本齐全，但尚未登记合同、支付或沟通材料，证据准备度不足。")
        return RiskResult("LOW", "核心事实和基础证据已登记，可以进入逐项核对；该等级表示信息准备度，不代表胜诉概率。")

    def generate_report(
        self,
        intent: IntentResult,
        extracted: ExtractionResult,
        completeness: CompletenessResult,
        knowledge: KnowledgeResult,
        risk: RiskResult,
    ) -> ReportResult:
        disclaimer = "本结果由演示模式生成，仅用于信息整理和风险提示，不构成法律意见或结果承诺。"
        if not intent.in_scope:
            return ReportResult(
                f"当前描述被识别为“{intent.label}”，不属于 V1.0 押金纠纷范围。",
                "UNSUPPORTED：当前版本不输出该场景的法律判断。",
                "未检索法律依据。",
                "请确认问题是否涉及押金返还；其他租房纠纷建议咨询专业人士。",
                "1. 重新描述押金金额、扣款方和扣款理由。\n2. 如确属其他纠纷，请使用相应专业服务。",
                disclaimer,
            )

        fact_parts = [intent.label]
        if extracted.amount:
            fact_parts.append(f"涉及金额约{extracted.amount}")
        if extracted.deduction_reason:
            fact_parts.append(f"对方理由为“{extracted.deduction_reason}”")

        legal_basis = "\n".join(
            f"- [{item['id']}] {item['title']}：{item['content']}（来源：{item['source_url']}）"
            for item in knowledge.references
        ) or "未检索到可核验依据，本次不输出法条判断。"

        standard_evidence = ["租赁合同", "押金支付记录", "对方扣款说明或聊天记录", "入住与退房交接材料", "维修或清洁费用凭证"]
        missing_evidence = "建议按优先级核对：" + "、".join(standard_evidence)
        if completeness.missing_fields:
            missing_evidence = f"先补充事实字段：{'、'.join(completeness.missing_fields)}。\n" + missing_evidence

        action_plan = (
            "1. 保存合同、押金支付记录和对方扣款说明的原始文件。\n"
            "2. 通过文字沟通要求对方列明扣款项目、金额和对应凭证。\n"
            "3. 对照入住/退房材料，区分正常使用损耗与具体损坏。\n"
            "4. 信息仍有争议时，携带完整材料咨询当地公共法律服务或专业律师。"
        )
        return ReportResult("；".join(fact_parts) + "。", f"{risk.level}：{risk.reason}", legal_basis, missing_evidence, action_plan, disclaimer)
