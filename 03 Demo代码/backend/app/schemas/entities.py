from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(SchemaBase):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    avatar: str | None = Field(default=None, max_length=255)


class UserUpdate(SchemaBase):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    avatar: str | None = Field(default=None, max_length=255)


class UserRead(SchemaBase):
    id: int
    username: str
    phone: str | None
    avatar: str | None
    create_time: datetime
    update_time: datetime


class CaseCreate(SchemaBase):
    user_id: int
    case_title: str | None = Field(default=None, max_length=100)
    case_type: str = Field(default="DEPOSIT", max_length=50)
    description: str | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    start_date: date | None = None
    end_date: date | None = None
    status: str = Field(default="CREATED", max_length=20)
    risk_level: str | None = Field(default=None, max_length=20)
    ai_status: str = Field(default="PENDING", max_length=20)


class CaseUpdate(SchemaBase):
    case_title: str | None = Field(default=None, max_length=100)
    case_type: str | None = Field(default=None, max_length=50)
    description: str | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = Field(default=None, max_length=20)
    risk_level: str | None = Field(default=None, max_length=20)
    ai_status: str | None = Field(default=None, max_length=20)


class CaseRead(CaseCreate):
    id: int
    create_time: datetime
    update_time: datetime


class EvidenceCreate(SchemaBase):
    case_id: int
    file_name: str | None = Field(default=None, max_length=255)
    file_url: str | None = Field(default=None, max_length=500)
    file_type: str | None = Field(default=None, max_length=50)
    evidence_type: str | None = Field(default=None, max_length=50)
    ai_summary: str | None = None
    importance_level: str | None = Field(default=None, max_length=20)
    extract_content: str | None = None


class EvidenceUpdate(SchemaBase):
    file_name: str | None = Field(default=None, max_length=255)
    file_url: str | None = Field(default=None, max_length=500)
    file_type: str | None = Field(default=None, max_length=50)
    evidence_type: str | None = Field(default=None, max_length=50)
    ai_summary: str | None = None
    importance_level: str | None = Field(default=None, max_length=20)
    extract_content: str | None = None


class EvidenceRead(EvidenceCreate):
    id: int
    upload_time: datetime


class ReportCreate(SchemaBase):
    case_id: int
    version: int = Field(default=1, ge=1)
    summary: str | None = None
    risk_analysis: str | None = None
    legal_basis: str | None = None
    missing_evidence: str | None = None
    action_plan: str | None = None
    disclaimer: str | None = None
    provider: str | None = Field(default=None, max_length=50)
    ai_model: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=50)
    knowledge_version: str | None = Field(default=None, max_length=100)
    token_usage: int | None = Field(default=None, ge=0)


class ReportUpdate(SchemaBase):
    version: int | None = Field(default=None, ge=1)
    summary: str | None = None
    risk_analysis: str | None = None
    legal_basis: str | None = None
    missing_evidence: str | None = None
    action_plan: str | None = None
    disclaimer: str | None = None
    provider: str | None = Field(default=None, max_length=50)
    ai_model: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=50)
    knowledge_version: str | None = Field(default=None, max_length=100)
    token_usage: int | None = Field(default=None, ge=0)


class ReportRead(ReportCreate):
    id: int
    create_time: datetime
    update_time: datetime


class TaskCreate(SchemaBase):
    case_id: int
    task_type: str = Field(max_length=50)
    prompt: str | None = None
    response: str | None = None
    status: str = Field(default="PENDING", max_length=20)
    latency: int | None = Field(default=None, ge=0)
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=50)
    knowledge_version: str | None = Field(default=None, max_length=100)
    token_usage: int | None = Field(default=None, ge=0)
    error_type: str | None = Field(default=None, max_length=100)


class TaskUpdate(SchemaBase):
    task_type: str | None = Field(default=None, max_length=50)
    prompt: str | None = None
    response: str | None = None
    status: str | None = Field(default=None, max_length=20)
    latency: int | None = Field(default=None, ge=0)
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=50)
    knowledge_version: str | None = Field(default=None, max_length=100)
    token_usage: int | None = Field(default=None, ge=0)
    error_type: str | None = Field(default=None, max_length=100)


class TaskRead(TaskCreate):
    id: int
    create_time: datetime


class AgentTraceRead(SchemaBase):
    task_type: str
    status: str
    latency: int
    token_usage: int = 0
    output: dict | list | str | None


class AnalysisRunRead(SchemaBase):
    case_id: int
    dispute_type: str
    completeness: bool
    completeness_score: float
    follow_up_questions: list[str]
    risk_level: str
    analysis_mode: str
    provider: str
    model: str
    prompt_version: str
    knowledge_version: str
    disclaimer: str
    retrieved_knowledge: list[dict[str, str]]
    report: ReportRead
    workflow: list[AgentTraceRead]
