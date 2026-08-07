from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


def get_or_404(db: Session, model: type[ModelType], entity_id: int, label: str) -> ModelType:
    entity = db.get(model, entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label}不存在")
    return entity


def list_entities(db: Session, model: type[ModelType], skip: int, limit: int) -> list[ModelType]:
    return list(db.scalars(select(model).offset(skip).limit(limit)).all())


def create_entity(db: Session, model: type[ModelType], values: dict[str, Any], label: str) -> ModelType:
    entity = model(**values)
    db.add(entity)
    return _commit_and_refresh(db, entity, label)


def update_entity(db: Session, entity: ModelType, values: dict[str, Any], label: str) -> ModelType:
    for field, value in values.items():
        setattr(entity, field, value)
    return _commit_and_refresh(db, entity, label)


def delete_entity(db: Session, entity: ModelType, label: str) -> None:
    db.delete(entity)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{label}删除失败") from error


def _commit_and_refresh(db: Session, entity: ModelType, label: str) -> ModelType:
    try:
        db.commit()
        db.refresh(entity)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{label}数据冲突") from error
    return entity
