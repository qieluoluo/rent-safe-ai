from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="服务健康检查")
def health_check() -> dict[str, str]:
    """供本地启动检查和部署探针调用。"""
    return {"status": "ok"}
