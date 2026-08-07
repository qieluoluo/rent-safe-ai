from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

PrimaryKeyType = BigInteger().with_variant(Integer, "sqlite")


class TimestampedModel:
    """包含创建时间的实体混入类。"""

    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(TimestampedModel, Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    avatar: Mapped[str | None] = mapped_column(String(255))

    cases: Mapped[list["CaseCase"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class CaseCase(TimestampedModel, Base):
    __tablename__ = "case_case"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False)
    case_title: Mapped[str | None] = mapped_column(String(100))
    case_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), index=True, default="CREATED", nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    ai_status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    user: Mapped[User] = relationship(back_populates="cases")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    reports: Mapped[list["AIReport"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    tasks: Mapped[list["AITask"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case_case.id", ondelete="CASCADE"), index=True, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_url: Mapped[str | None] = mapped_column(String(500))
    file_type: Mapped[str | None] = mapped_column(String(50))
    evidence_type: Mapped[str | None] = mapped_column(String(50), index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    importance_level: Mapped[str | None] = mapped_column(String(20))
    extract_content: Mapped[str | None] = mapped_column(Text)
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    case: Mapped[CaseCase] = relationship(back_populates="evidences")


class AIReport(TimestampedModel, Base):
    __tablename__ = "ai_report"
    __table_args__ = (UniqueConstraint("case_id", "version", name="uq_report_case_version"),)

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case_case.id", ondelete="CASCADE"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    risk_analysis: Mapped[str | None] = mapped_column(Text)
    legal_basis: Mapped[str | None] = mapped_column(Text)
    missing_evidence: Mapped[str | None] = mapped_column(Text)
    action_plan: Mapped[str | None] = mapped_column(Text)
    disclaimer: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(50))
    ai_model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    knowledge_version: Mapped[str | None] = mapped_column(String(100))
    token_usage: Mapped[int | None] = mapped_column(Integer)

    case: Mapped[CaseCase] = relationship(back_populates="reports")


class AITask(Base):
    __tablename__ = "ai_task"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case_case.id", ondelete="CASCADE"), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    prompt: Mapped[str | None] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), index=True, default="PENDING", nullable=False)
    latency: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    knowledge_version: Mapped[str | None] = mapped_column(String(100))
    token_usage: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(100))
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    case: Mapped[CaseCase] = relationship(back_populates="tasks")
