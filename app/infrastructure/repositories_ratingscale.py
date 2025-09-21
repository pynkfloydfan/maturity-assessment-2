# app/infrastructure/repositories_ratingscale.py
from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, NoReturn

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# App exceptions
from .exceptions import ValidationError
from .models import RatingScaleORM

# Use the generic base (typed) — alias to avoid any name collision elsewhere
from .repositories_base import BaseRepository as GenericBaseRepository

# Logging decorator(s)
try:
    from .logging import log_database_operation as log_op
except ImportError:
    from .logging import log_operation as log_op


class RatingScaleRepo(GenericBaseRepository[RatingScaleORM]):
    """
    Repository for rating scale database operations.

    Handles CRUD operations for CMMI rating scale definitions
    with proper validation and error handling.
    """

    model = RatingScaleORM

    def __init__(self, session: Session):
        super().__init__(session)
        # Back-compat: some existing code references self.session / _handle_error
        self.session = self.s
        self._logger = logging.getLogger(__name__)

    # ----- internal error helper (back-compat with old BaseRepository) -----
    def _handle_error(self, exc: Exception, operation: str) -> NoReturn:
        """
        Mirror the behavior your old BaseRepository provided:
        - Log the exception with operation context
        - Re-raise so the API layer can wrap consistently (ResilienceAssessmentError)
        """
        try:
            self._logger.exception("DB error in %s: %s", operation, str(exc))
        finally:
            raise  # re-raise original exception

    # ------------------- Operations -------------------

    @log_op("upsert_rating_scale")
    def upsert(self, level: int, label: str) -> RatingScaleORM:
        """
        Create or update rating scale entry.
        """
        if not (1 <= level <= 5):
            raise ValidationError("level", "Rating level must be between 1-5")
        if not label or not label.strip():
            raise ValidationError("label", "Rating label cannot be empty")

        try:
            obj = self.session.get(RatingScaleORM, level)
            if obj is None:
                obj = RatingScaleORM(level=level, label=label.strip())
                self.session.add(obj)
            else:
                obj.label = label.strip()
            self.session.flush()
            return obj
        except SQLAlchemyError as e:
            self._handle_error(e, "upsert_rating_scale")

    @log_op("list_rating_scales")
    def list_all(self, order_by: Iterable[Any] | None = None) -> list[RatingScaleORM]:
        """
        Get all rating scale entries ordered by level.
        """
        if order_by is not None:
            return super().list(order_by=order_by)

        try:
            return self.session.query(RatingScaleORM).order_by(RatingScaleORM.level).all()
        except SQLAlchemyError as e:
            self._handle_error(e, "list_rating_scales")

    @log_op("get_rating_scale")
    def get_by_level(self, level: int) -> RatingScaleORM | None:
        """
        Get rating scale by level.
        """
        if not (1 <= level <= 5):
            raise ValidationError("level", "Rating level must be between 1-5")

        try:
            return self.session.get(RatingScaleORM, level)
        except SQLAlchemyError as e:
            self._handle_error(e, "get_rating_scale")
