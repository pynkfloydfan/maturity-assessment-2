from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from .models import AcronymORM
from .repositories_base import BaseRepository as GenericBaseRepository

try:
    from .logging import log_database_operation as log_op
except ImportError:  # pragma: no cover
    from .logging import log_operation as log_op


class AcronymRepo(GenericBaseRepository[AcronymORM]):
    model = AcronymORM

    def __init__(self, session: Session):
        super().__init__(session)

    @log_op("acronym.list_all")
    def list_all(self, order_by: Iterable[Any] | None = None) -> list[AcronymORM]:
        if order_by is None and hasattr(self.model, "acronym"):
            order_by = [self.model.acronym.asc()]
        return super().list(order_by=order_by)
