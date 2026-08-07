from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.resources import router as resources_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["健康检查"])
api_router.include_router(resources_router, tags=["基础数据"])
