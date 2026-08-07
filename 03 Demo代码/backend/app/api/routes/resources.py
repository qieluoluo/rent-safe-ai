from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.crud import create_entity, delete_entity, get_or_404, list_entities, update_entity
from app.core.security import hash_password
from app.db.session import get_db
from app.models import AITask, AIReport, CaseCase, Evidence, User
from app.schemas.entities import (
    CaseCreate,
    CaseRead,
    CaseUpdate,
    EvidenceCreate,
    EvidenceRead,
    EvidenceUpdate,
    ReportCreate,
    ReportRead,
    ReportUpdate,
    TaskCreate,
    TaskRead,
    TaskUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession) -> User:
    values = payload.model_dump()
    values["password"] = hash_password(values["password"])
    return create_entity(db, User, values, "用户")


@router.get("/users", response_model=list[UserRead])
def list_users(db: DbSession, skip: int = 0, limit: int = 100) -> list[User]:
    return list_entities(db, User, skip, limit)


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSession) -> User:
    return get_or_404(db, User, user_id, "用户")


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: DbSession) -> User:
    values = payload.model_dump(exclude_unset=True)
    if "password" in values:
        values["password"] = hash_password(values["password"])
    return update_entity(db, get_or_404(db, User, user_id, "用户"), values, "用户")


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DbSession) -> Response:
    delete_entity(db, get_or_404(db, User, user_id, "用户"), "用户")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cases", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, db: DbSession) -> CaseCase:
    get_or_404(db, User, payload.user_id, "用户")
    return create_entity(db, CaseCase, payload.model_dump(), "案件")


@router.get("/cases", response_model=list[CaseRead])
def list_cases(db: DbSession, skip: int = 0, limit: int = 100) -> list[CaseCase]:
    return list_entities(db, CaseCase, skip, limit)


@router.get("/cases/{case_id}", response_model=CaseRead)
def get_case(case_id: int, db: DbSession) -> CaseCase:
    return get_or_404(db, CaseCase, case_id, "案件")


@router.patch("/cases/{case_id}", response_model=CaseRead)
def update_case(case_id: int, payload: CaseUpdate, db: DbSession) -> CaseCase:
    return update_entity(db, get_or_404(db, CaseCase, case_id, "案件"), payload.model_dump(exclude_unset=True), "案件")


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: int, db: DbSession) -> Response:
    delete_entity(db, get_or_404(db, CaseCase, case_id, "案件"), "案件")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/evidences", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(payload: EvidenceCreate, db: DbSession) -> Evidence:
    get_or_404(db, CaseCase, payload.case_id, "案件")
    return create_entity(db, Evidence, payload.model_dump(), "证据")


@router.get("/evidences", response_model=list[EvidenceRead])
def list_evidences(db: DbSession, skip: int = 0, limit: int = 100) -> list[Evidence]:
    return list_entities(db, Evidence, skip, limit)


@router.get("/evidences/{evidence_id}", response_model=EvidenceRead)
def get_evidence(evidence_id: int, db: DbSession) -> Evidence:
    return get_or_404(db, Evidence, evidence_id, "证据")


@router.patch("/evidences/{evidence_id}", response_model=EvidenceRead)
def update_evidence(evidence_id: int, payload: EvidenceUpdate, db: DbSession) -> Evidence:
    return update_entity(db, get_or_404(db, Evidence, evidence_id, "证据"), payload.model_dump(exclude_unset=True), "证据")


@router.delete("/evidences/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: int, db: DbSession) -> Response:
    delete_entity(db, get_or_404(db, Evidence, evidence_id, "证据"), "证据")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reports", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, db: DbSession) -> AIReport:
    get_or_404(db, CaseCase, payload.case_id, "案件")
    return create_entity(db, AIReport, payload.model_dump(), "AI报告")


@router.get("/reports", response_model=list[ReportRead])
def list_reports(db: DbSession, skip: int = 0, limit: int = 100) -> list[AIReport]:
    return list_entities(db, AIReport, skip, limit)


@router.get("/reports/{report_id}", response_model=ReportRead)
def get_report(report_id: int, db: DbSession) -> AIReport:
    return get_or_404(db, AIReport, report_id, "AI报告")


@router.patch("/reports/{report_id}", response_model=ReportRead)
def update_report(report_id: int, payload: ReportUpdate, db: DbSession) -> AIReport:
    return update_entity(db, get_or_404(db, AIReport, report_id, "AI报告"), payload.model_dump(exclude_unset=True), "AI报告")


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, db: DbSession) -> Response:
    delete_entity(db, get_or_404(db, AIReport, report_id, "AI报告"), "AI报告")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession) -> AITask:
    get_or_404(db, CaseCase, payload.case_id, "案件")
    return create_entity(db, AITask, payload.model_dump(), "AI任务")


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(db: DbSession, skip: int = 0, limit: int = 100) -> list[AITask]:
    return list_entities(db, AITask, skip, limit)


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DbSession) -> AITask:
    return get_or_404(db, AITask, task_id, "AI任务")


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: DbSession) -> AITask:
    return update_entity(db, get_or_404(db, AITask, task_id, "AI任务"), payload.model_dump(exclude_unset=True), "AI任务")


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession) -> Response:
    delete_entity(db, get_or_404(db, AITask, task_id, "AI任务"), "AI任务")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
