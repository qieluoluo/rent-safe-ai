from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """所有业务接口共用的响应结构。"""

    code: int = 0
    message: str = "success"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


def success(data: T | None = None, message: str = "success") -> ApiResponse[T]:
    return ApiResponse(code=0, message=message, data=data)
