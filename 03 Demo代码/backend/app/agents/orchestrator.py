import json
import re
from dataclasses import asdict
from time import perf_counter
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.mock_provider import MockAnalysisProvider
from app.agents.provider_factory import build_analysis_provider
from app.core.config import get_settings
from app.models import AIReport, AITask, CaseCase, Evidence

ResultType = TypeVar("ResultType")


class AnalysisOrchestrator:
    """将六个 Agent 步骤串联，并把每一步记录到 ai_task。"""

    def __init__(self, provider: MockAnalysisProvider | None = None) -> None:
        self.provider = provider or build_analysis_provider(get_settings())

    def run(self, db: Session, case: CaseCase) -> dict[str, Any]:
        description = (case.description or "").strip()
        if not description:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="案件缺少纠纷描述，无法启动分析")

        case.status = "ANALYZING"
        case.ai_status = "PROCESSING"
        db.commit()

        workflow: list[dict[str, Any]] = []
        try:
            intent = self._run_step(db, case.id, "INTENT", description, lambda: self.provider.identify_intent(description, case.case_type), workflow)
            extracted = self._run_step(db, case.id, "EXTRACT", description, lambda: self.provider.extract_information(description, case.amount), workflow)
            completeness = self._run_step(db, case.id, "COMPLETENESS", description, lambda: self.provider.assess_completeness(extracted), workflow)
            knowledge = self._run_step(db, case.id, "KNOWLEDGE", description, lambda: self.provider.retrieve_knowledge(intent, description), workflow)
            evidence_count = db.scalar(select(func.count()).select_from(Evidence).where(Evidence.case_id == case.id)) or 0
            risk = self._run_step(db, case.id, "RISK", description, lambda: self.provider.analyze_risk(completeness, evidence_count), workflow)
            report_data = self._run_step(db, case.id, "REPORT", description, lambda: self.provider.generate_report(intent, extracted, completeness, knowledge, risk), workflow)
        except Exception:
            case.ai_status = "FAILED"
            case.status = "CREATED"
            db.commit()
            raise

        version = (db.scalar(select(func.max(AIReport.version)).where(AIReport.case_id == case.id)) or 0) + 1
        report = AIReport(
            case_id=case.id,
            version=version,
            summary=report_data.summary,
            risk_analysis=report_data.risk,
            legal_basis=report_data.legal_basis,
            missing_evidence=report_data.missing_evidence,
            action_plan=report_data.action_plan,
            disclaimer=report_data.disclaimer,
            provider=self.provider.provider_name,
            ai_model=self.provider.model_name,
            prompt_version=self.provider.prompt_version,
            knowledge_version=knowledge.knowledge_version,
            token_usage=sum(int(step.get("token_usage", 0)) for step in workflow),
        )
        db.add(report)
        case.case_type = intent.case_type
        case.risk_level = risk.level
        case.ai_status = "DONE"
        case.status = "COMPLETED" if completeness.is_complete else "WAITING"
        db.commit()
        db.refresh(report)

        return {
            "case_id": case.id,
            "dispute_type": intent.label,
            "completeness": completeness.is_complete,
            "completeness_score": completeness.score,
            "follow_up_questions": completeness.follow_up_questions,
            "risk_level": risk.level,
            "analysis_mode": "DEMO" if self.provider.provider_name == "mock" else "MODEL_ASSISTED",
            "provider": self.provider.provider_name,
            "model": self.provider.model_name,
            "prompt_version": self.provider.prompt_version,
            "knowledge_version": knowledge.knowledge_version,
            "disclaimer": report_data.disclaimer,
            "retrieved_knowledge": knowledge.references,
            "report": report,
            "workflow": workflow,
        }

    def _run_step(
        self,
        db: Session,
        case_id: int,
        task_type: str,
        prompt: str,
        handler: Callable[[], ResultType],
        workflow: list[dict[str, Any]],
    ) -> ResultType:
        start = perf_counter()
        try:
            result = handler()
            response = asdict(result)
            latency = int((perf_counter() - start) * 1000)
            token_usage = int(getattr(self.provider, "last_token_usage", 0) or 0)
            if hasattr(self.provider, "last_token_usage"):
                self.provider.last_token_usage = 0
            task = AITask(
                case_id=case_id,
                task_type=task_type,
                prompt=self._redact_prompt(prompt),
                response=json.dumps(response, ensure_ascii=False),
                status="SUCCESS",
                latency=latency,
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                prompt_version=self.provider.prompt_version,
                knowledge_version=getattr(self.provider, "knowledge_version", None),
                token_usage=token_usage,
            )
            db.add(task)
            db.commit()
            workflow.append({"task_type": task_type, "status": "SUCCESS", "latency": latency, "token_usage": token_usage, "output": response})
            return result
        except Exception as error:
            latency = int((perf_counter() - start) * 1000)
            db.add(
                AITask(
                    case_id=case_id,
                    task_type=task_type,
                    prompt=self._redact_prompt(prompt),
                    response=str(error)[:2000],
                    status="FAILED",
                    latency=latency,
                    provider=self.provider.provider_name,
                    model=self.provider.model_name,
                    prompt_version=self.provider.prompt_version,
                    knowledge_version=getattr(self.provider, "knowledge_version", None),
                    error_type=type(error).__name__,
                )
            )
            db.commit()
            raise

    @staticmethod
    def _redact_prompt(prompt: str) -> str:
        """日志仅保留脱敏输入，避免手机号和身份证号直接落库。"""
        redacted = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号已脱敏]", prompt)
        redacted = re.sub(r"(?<!\d)\d{17}[\dXx](?!\d)", "[身份证号已脱敏]", redacted)
        return redacted[:4000]
