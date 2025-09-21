# app/infrastructure/repositories_session.py
from __future__ import annotations

import builtins
from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from .models import AssessmentSessionORM

# Use the generic base (typed) — alias to avoid any name collision elsewhere
from .repositories_base import BaseRepository as GenericBaseRepository

# Use your existing logging decorator. If the DB-specific one isn't present,
# fall back to the generic log_operation to keep behavior.
try:
    from .logging import log_database_operation as log_op
except ImportError:
    from .logging import log_operation as log_op


class SessionRepo(GenericBaseRepository[AssessmentSessionORM]):
    model = AssessmentSessionORM

    def __init__(self, session: Session):
        super().__init__(session)

    # -------- Read --------

    @log_op("session.get")
    def get(self, id_: Any) -> AssessmentSessionORM | None:
        return super().get(id_)

    @log_op("session.get_required")
    def get_by_id_required(self, id_: Any) -> AssessmentSessionORM:
        return super().get_by_id_required(id_)

    @log_op("session.list")
    def list(
        self,
        *filters: Any,
        order_by: Iterable[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> builtins.list[AssessmentSessionORM]:
        return super().list(*filters, order_by=order_by, limit=limit, offset=offset)

    @log_op("session.exists")
    def exists(self, *filters: Any) -> bool:
        return super().exists(*filters)

    @log_op("session.count")
    def count(self, *filters: Any) -> int:
        return super().count(*filters)

    # -------- Write --------

    @log_op("session.create")
    def create(self, **fields: Any) -> AssessmentSessionORM:
        return super().create(**fields)

    @log_op("session.update")
    def update(self, obj: AssessmentSessionORM, **fields: Any) -> AssessmentSessionORM:
        return super().update(obj, **fields)

    @log_op("session.delete")
    def delete(self, obj: AssessmentSessionORM) -> None:
        super().delete(obj)

    # -------- Custom helpers --------

    @log_op("session.latest")
    def latest(self) -> AssessmentSessionORM | None:
        q = self.s.query(self.model)
        if hasattr(self.model, "created_at"):
            q = q.order_by(self.model.created_at.desc())
        else:
            q = q.order_by(self.model.id.desc())
        return q.limit(1).one_or_none()

    @log_op("session.list_all")
    def list_all(
        self, order_by: Iterable[Any] | None = None
    ) -> builtins.list[AssessmentSessionORM]:
        # Default ordering: newest first by created_at if present, else by id
        if order_by is not None:
            return super().list(order_by=order_by)

        if hasattr(self.model, "created_at"):
            order_expr: Any = self.model.created_at.desc()
        else:
            order_expr = self.model.id.desc()
        return super().list(order_by=[order_expr])
