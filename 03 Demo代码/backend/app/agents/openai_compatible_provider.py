import json
from dataclasses import asdict
from decimal import Decimal
from urllib import error, request

from app.agents.mock_provider import MockAnalysisProvider
from app.agents.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_TEMPLATE,
    INTENT_SYSTEM_PROMPT,
    INTENT_USER_TEMPLATE,
    PROMPT_VERSION,
    REPORT_SYSTEM_PROMPT,
    REPORT_USER_TEMPLATE,
)
from app.agents.types import CompletenessResult, ExtractionResult, IntentResult, KnowledgeResult, ReportResult, RiskResult
from app.core.config import Settings


class OpenAICompatibleAnalysisProvider(MockAnalysisProvider):
    """调用 OpenAI-compatible Chat Completions 的可选 Provider。

    默认配置面向 DeepSeek；未配置 API Key 时不会被实例化，Mock 基线仍可零配置运行。
    知识检索、完整度和信息准备风险保持确定性，便于复现和控制法律边界。
    """

    provider_name = "openai-compatible"
    prompt_version = PROMPT_VERSION

    def __init__(self, settings: Settings) -> None:
        if not settings.llm_api_key:
            raise ValueError("选择真实模型 Provider 时必须配置 LLM_API_KEY")
        self.api_base = settings.llm_api_base.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model_name = settings.llm_model
        self.timeout = settings.llm_timeout_seconds
        self.last_token_usage = 0

    def identify_intent(self, description: str, fallback_type: str = "DEPOSIT") -> IntentResult:
        payload = self._chat_json(INTENT_SYSTEM_PROMPT, INTENT_USER_TEMPLATE.format(description=description))
        case_type = str(payload.get("case_type", "UNKNOWN")).upper()
        in_scope = case_type == "DEPOSIT" and bool(payload.get("in_scope", True))
        if case_type not in {"DEPOSIT", "OUT_OF_SCOPE", "UNKNOWN"}:
            case_type, in_scope = "UNKNOWN", False
        return IntentResult(
            case_type,
            str(payload.get("label") or ("押金返还纠纷" if in_scope else "当前版本暂不支持该问题")),
            max(0.0, min(float(payload.get("confidence", 0.0)), 1.0)),
            in_scope,
        )

    def extract_information(self, description: str, amount: Decimal | None) -> ExtractionResult:
        payload = self._chat_json(
            EXTRACTION_SYSTEM_PROMPT,
            EXTRACTION_USER_TEMPLATE.format(description=description, amount=str(amount) if amount is not None else "null"),
        )
        lease_status = str(payload.get("lease_status", "UNKNOWN")).upper()
        if lease_status not in {"EXPIRED", "ONGOING", "UNKNOWN"}:
            lease_status = "UNKNOWN"
        return ExtractionResult(
            self._optional_text(payload.get("lease_period")),
            self._optional_text(payload.get("amount")),
            self._string_list(payload.get("roles")),
            self._string_list(payload.get("disputes")),
            lease_status,
            self._optional_text(payload.get("deduction_reason")),
        )

    def generate_report(
        self,
        intent: IntentResult,
        extracted: ExtractionResult,
        completeness: CompletenessResult,
        knowledge: KnowledgeResult,
        risk: RiskResult,
    ) -> ReportResult:
        if not intent.in_scope:
            return super().generate_report(intent, extracted, completeness, knowledge, risk)

        payload = self._chat_json(
            REPORT_SYSTEM_PROMPT,
            REPORT_USER_TEMPLATE.format(
                facts=json.dumps(asdict(extracted), ensure_ascii=False),
                completeness=json.dumps(asdict(completeness), ensure_ascii=False),
                risk=json.dumps(asdict(risk), ensure_ascii=False),
                knowledge=json.dumps(knowledge.references, ensure_ascii=False),
            ),
        )
        legal_basis = "\n".join(
            f"- [{item['id']}] {item['title']}：{item['content']}（来源：{item['source_url']}）"
            for item in knowledge.references
        ) or "未检索到可核验依据，本次不输出法条判断。"
        return ReportResult(
            str(payload.get("summary") or "信息不足，暂无法生成事实摘要。"),
            f"{risk.level}：{str(payload.get('risk_explanation') or risk.reason)}",
            legal_basis,
            str(payload.get("missing_evidence") or "请补充合同、支付和沟通记录。"),
            str(payload.get("action_plan") or "请先补齐关键信息，并保留原始证据。"),
            "本结果由大模型辅助生成，仅用于信息整理和风险提示，不构成法律意见或结果承诺。",
        )

    def _chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        body = json.dumps(
            {
                "model": self.model_name,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        http_request = request.Request(
            f"{self.api_base}/chat/completions",
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"模型接口返回 HTTP {exc.code}: {detail}") from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"模型接口调用失败: {exc}") from exc

        self.last_token_usage = int(result.get("usage", {}).get("total_tokens", 0) or 0)
        try:
            content = result["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("模型未返回可解析的 JSON 对象") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("模型输出必须是 JSON 对象")
        return parsed

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]
