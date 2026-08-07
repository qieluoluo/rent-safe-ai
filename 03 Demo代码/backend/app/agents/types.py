from dataclasses import dataclass


@dataclass
class IntentResult:
    case_type: str
    label: str
    confidence: float
    in_scope: bool


@dataclass
class ExtractionResult:
    lease_period: str | None
    amount: str | None
    roles: list[str]
    disputes: list[str]
    lease_status: str
    deduction_reason: str | None


@dataclass
class CompletenessResult:
    is_complete: bool
    score: float
    core_fields_complete: bool
    missing_fields: list[str]
    follow_up_questions: list[str]


@dataclass
class KnowledgeResult:
    references: list[dict[str, str]]
    knowledge_version: str


@dataclass
class RiskResult:
    level: str
    reason: str


@dataclass
class ReportResult:
    summary: str
    risk: str
    legal_basis: str
    missing_evidence: str
    action_plan: str
    disclaimer: str
