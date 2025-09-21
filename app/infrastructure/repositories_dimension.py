# app/infrastructure/repositories_dimension.py
from __future__ import annotations

import builtins
import logging
from collections.abc import Iterable
from typing import Any, NoReturn

from sqlalchemy.exc import IntegrityError as SQLIntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

# If DimensionInput lives somewhere else in your project, adjust this import path:
from ..domain.schemas import DimensionInput  # <-- adjust if your DimensionInput lives elsewhere

# Validation schema and app exceptions
from .exceptions import ValidationError
from .models import DimensionORM

# Use the generic base (typed) — alias to avoid any name collision elsewhere
from .repositories_base import BaseRepository as GenericBaseRepository

# Logging decorator(s)
try:
    from .logging import log_database_operation as log_op
except ImportError:
    # Fallback: if only a generic log decorator exists
    from .logging import log_operation as log_op


class DimensionRepo(GenericBaseRepository[DimensionORM]):
    """
    Repository for dimension-related database operations.

    Handles CRUD operations for organizational resilience dimensions
    with proper validation and error handling.

    Example:
        >>> repo = DimensionRepo(session)
        >>> dimension = repo.get_by_name("Technology")
        >>> if dimension:
        ...     print(f"Found: {dimension.name}")
    """

    model = DimensionORM

    def __init__(self, session: Session):
        super().__init__(session)
        # Back-compat: some existing repo code references self.session
        self.session = self.s  # alias to the Session for compatibility
        self._logger = logging.getLogger(__name__)

    # ----- internal error helper (back-compat with old BaseRepository) -----
    def _handle_error(self, exc: Exception, operation: str) -> NoReturn:
        """
        Mirror the behavior your old BaseRepository provided:
        - Log the exception with operation context
        - Re-raise so the API layer can wrap consistently (ResilienceAssessmentError)
        """
        # Prefer your project's logger if present; std logging works fine as a fallback
        try:
            self._logger.exception("DB error in %s: %s", operation, str(exc))
        finally:
            raise  # re-raise original exception

    # ------------------- Operations -------------------

    @log_op("get_dimension_by_name")
    def get_by_name(self, name: str) -> DimensionORM | None:
        """
        Get dimension by name.

        Args:
            name: Dimension name to search for

        Returns:
            DimensionORM instance if found, None otherwise

        Raises:
            ValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ValidationError("name", "Dimension name cannot be empty")

        try:
            return self.session.query(DimensionORM).filter_by(name=name.strip()).one_or_none()
        except SQLAlchemyError as e:
            self._handle_error(e, "get_dimension_by_name")

    @log_op("get_dimension_by_id")
    def get_by_id(self, dimension_id: int) -> DimensionORM | None:
        """
        Get dimension by ID.

        Args:
            dimension_id: Dimension ID to search for

        Returns:
            DimensionORM instance if found, None otherwise
        """
        if dimension_id <= 0:
            raise ValidationError("dimension_id", "Dimension ID must be positive")

        try:
            return self.session.get(DimensionORM, dimension_id)
        except SQLAlchemyError as e:
            self._handle_error(e, "get_dimension_by_id")

    @log_op("create_dimension")
    def create(self, name: str | None = None, **_: Any) -> DimensionORM:
        """
        Create new dimension.

        Args:
            name: Dimension name

        Returns:
            Created DimensionORM instance

        Raises:
            ValidationError: If input is invalid
            IntegrityError: If dimension name already exists
        """
        if name is None:
            raise ValidationError("name", "Dimension name cannot be empty")

        validated_data = DimensionInput(name=name)

        try:
            dimension = DimensionORM(name=validated_data.name)
            self.session.add(dimension)
            self.session.flush()  # Get ID without committing
            return dimension
        except SQLIntegrityError as e:
            self._handle_error(e, "create_dimension")
        except SQLAlchemyError as e:
            self._handle_error(e, "create_dimension")

    @log_op("list_dimensions")
    def list(
        self,
        *filters: Any,
        order_by: Iterable[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> builtins.list[DimensionORM]:
        """
        Get all dimensions ordered by name.
        """
        if filters or order_by is not None or limit is not None or offset is not None:
            return super().list(*filters, order_by=order_by, limit=limit, offset=offset)

        try:
            return self.session.query(DimensionORM).order_by(DimensionORM.name).all()
        except SQLAlchemyError as e:
            self._handle_error(e, "list_dimensions")

    @log_op("list_dimensions_with_themes")
    def list_with_themes(self) -> builtins.list[DimensionORM]:
        """
        Get all dimensions with eagerly loaded themes.
        """
        try:
            return (
                self.session.query(DimensionORM)
                .options(joinedload(DimensionORM.themes))
                .order_by(DimensionORM.name)
                .all()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "list_dimensions_with_themes")
