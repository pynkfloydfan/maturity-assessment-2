# app/infrastructure/repositories_base.py
from __future__ import annotations

import builtins
from collections.abc import Iterable
from typing import Any, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")  # ORM model type


class BaseRepository[T]:
    """
    Lightweight generic repository with common CRUD + query helpers.
    - Intentionally small and decoupled from app-specific logging/decorators.
    - Entity repos can override methods and add decorators (logging, metrics) as needed.
    """

    model: type[T]  # must be set by subclasses

    def __init__(self, session: Session):
        if not hasattr(self, "model") or self.model is None:
            raise ValueError(f"{self.__class__.__name__}.model must be set to an ORM class.")
        self.s = session

    # ---------- Read ----------
    def get(self, id_: Any) -> T | None:
        return self.s.get(self.model, id_)

    def get_by_id_required(self, id_: Any) -> T:
        obj = self.get(id_)
        if obj is None:
            raise ValueError(f"{self.model.__name__} with id {id_} not found")
        return obj

    def list(
        self,
        *filters: Any,
        order_by: Iterable[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> builtins.list[T]:
        q = self.s.query(self.model)
        for f in filters:
            q = q.filter(f)
        if order_by:
            for ob in order_by:
                q = q.order_by(ob)
        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)
        return list(q.all())

    def list_all(
        self,
        order_by: Iterable[Any] | None = None,
    ) -> builtins.list[T]:
        """Backward-compatible alias for code that expects `list_all()`."""
        return self.list(order_by=order_by)

    def exists(self, *filters: Any) -> bool:
        q = self.s.query(self.model)
        for f in filters:
            q = q.filter(f)
        result = self.s.query(q.exists()).scalar()
        return bool(result)

    def count(self, *filters: Any) -> int:
        q = self.s.query(self.model)
        for f in filters:
            q = q.filter(f)
        return int(q.count())

    # ---------- Write ----------
    def create(self, **fields: Any) -> T:
        obj = self.model(**fields)
        self.s.add(obj)
        self.s.flush()  # get PKs without committing
        return obj

    def update(self, obj: T, **fields: Any) -> T:
        for k, v in fields.items():
            setattr(obj, k, v)
        self.s.flush()
        return obj

    def delete(self, obj: T) -> None:
        self.s.delete(obj)
        self.s.flush()
