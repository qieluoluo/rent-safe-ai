import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import create_entity, get_or_404
from app.agents.orchestrator import AnalysisOrchestrator
from app.db.session import get_db
from app.models import AIReport, AITask, CaseCase, Evidence, User
from app.schemas.entities import AnalysisRunRead, AgentTraceRead, CaseCreate, CaseRead, EvidenceRead, ReportRead
from app.schemas.response import ApiResponse, PageData, success
from app.services.file_storage import save_evidence_file

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/cases", response_model=ApiResponse[CaseRead], status_code=status.HTTP_201_CREATED, summary="创建案件")
def create_case(payload: CaseCreate, db: DbSession) -> ApiResponse[CaseRead]:
    get_or_404(db, User, payload.user_id, "用户")
    case = create_entity(db, CaseCase, payload.model_dump(), "案件")
    return success(CaseRead.model_validate(case), "案件创建成功")


@router.get("/cases", response_model=ApiResponse[PageData[CaseRead]], summary="获取案件列表")
def list_cases(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    case_type: Annotated[str | None, Query(max_length=50)] = None,
    case_status: Annotated[str | None, Query(max_length=20)] = None,
) -> ApiResponse[PageData[CaseRead]]:
    filters = []
    if user_id is not None:
        filters.append(CaseCase.user_id == user_id)
    if case_type is not None:
        filters.append(CaseCase.case_type == case_type)
    if case_status is not None:
        filters.append(CaseCase.status == case_status)

    total = db.scalar(select(func.count()).select_from(CaseCase).where(*filters)) or 0
    statement = (
        select(CaseCase)
        .where(*filters)
        .order_by(CaseCase.create_time.desc(), CaseCase.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    cases = db.scalars(statement).all()
    result = PageData(
        items=[CaseRead.model_validate(case) for case in cases],
        total=total,
        page=page,
        page_size=page_size,
    )
    return success(result)


@router.get("/cases/{case_id}", response_model=ApiResponse[CaseRead], summary="查看案件详情")
def get_case(case_id: Annotated[int, Path(gt=0)], db: DbSession) -> ApiResponse[CaseRead]:
    case = get_or_404(db, CaseCase, case_id, "案件")
    return success(CaseRead.model_validate(case))


@router.post(
    "/cases/{case_id}/analysis",
    response_model=ApiResponse[AnalysisRunRead],
    summary="运行租房纠纷智能分析",
)
def run_case_analysis(case_id: Annotated[int, Path(gt=0)], db: DbSession) -> ApiResponse[AnalysisRunRead]:
    """执行范围识别、信息抽取、完整度、知识检索、风险和报告六步工作流。"""
    case = get_or_404(db, CaseCase, case_id, "案件")
    try:
        orchestrator = AnalysisOrchestrator()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    result = orchestrator.run(db, case)
    result["report"] = ReportRead.model_validate(result["report"])
    mode_label = "演示模式" if result["analysis_mode"] == "DEMO" else "模型辅助模式"
    return success(AnalysisRunRead.model_validate(result), f"{mode_label}分析完成")


@router.get(
    "/cases/{case_id}/analysis/tasks",
    response_model=ApiResponse[list[AgentTraceRead]],
    summary="获取 AI Agent 工作流轨迹",
)
def get_analysis_tasks(case_id: Annotated[int, Path(gt=0)], db: DbSession) -> ApiResponse[list[AgentTraceRead]]:
    get_or_404(db, CaseCase, case_id, "案件")
    tasks = db.scalars(select(AITask).where(AITask.case_id == case_id).order_by(AITask.id.desc())).all()
    traces = []
    for task in tasks:
        try:
            output = json.loads(task.response) if task.response else None
        except json.JSONDecodeError:
            output = task.response
        traces.append(
            AgentTraceRead(
                task_type=task.task_type,
                status=task.status,
                latency=task.latency or 0,
                token_usage=task.token_usage or 0,
                output=output,
            )
        )
    return success(traces)


@router.post(
    "/evidence/upload",
    response_model=ApiResponse[EvidenceRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传证据",
)
async def upload_evidence(
    db: DbSession,
    case_id: Annotated[int, Form(gt=0)],
    file: Annotated[UploadFile, File(description="PDF、图片或文档，最大 20MB")],
    evidence_type: Annotated[str | None, Form(max_length=50)] = None,
) -> ApiResponse[EvidenceRead]:
    get_or_404(db, CaseCase, case_id, "案件")
    file_name, file_url, file_type = await save_evidence_file(file)
    evidence = create_entity(
        db,
        Evidence,
        {
            "case_id": case_id,
            "file_name": file_name,
            "file_url": file_url,
            "file_type": file_type,
            "evidence_type": evidence_type,
        },
        "证据",
    )
    return success(EvidenceRead.model_validate(evidence), "证据上传成功")


@router.get("/evidence/{case_id}", response_model=ApiResponse[list[EvidenceRead]], summary="获取案件证据")
def list_case_evidence(case_id: Annotated[int, Path(gt=0)], db: DbSession) -> ApiResponse[list[EvidenceRead]]:
    get_or_404(db, CaseCase, case_id, "案件")
    evidences = db.scalars(select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.id.desc())).all()
    return success([EvidenceRead.model_validate(evidence) for evidence in evidences])


@router.get("/report/{case_id}", response_model=ApiResponse[ReportRead], summary="获取最新AI分析报告")
def get_latest_report(case_id: Annotated[int, Path(gt=0)], db: DbSession) -> ApiResponse[ReportRead]:
    get_or_404(db, CaseCase, case_id, "案件")
    report = db.scalar(
        select(AIReport)
        .where(AIReport.case_id == case_id)
        .order_by(AIReport.version.desc(), AIReport.id.desc())
        .limit(1)
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该案件暂无分析报告")
    return success(ReportRead.model_validate(report))
