# app/infrastructure/repositories_theme.py
from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError as SQLIntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

# Adjust the import below if ThemeInput lives elsewhere
from ..domain.schemas import ThemeInput  # <-- if needed, change to your actual path

# Validation schema and app exceptions
from .exceptions import ValidationError
from .models import ThemeORM

# Use the generic base (typed) — alias to avoid any name collision elsewhere
from .repositories_base import BaseRepository as GenericBaseRepository

# Logging decorator(s)
try:
    from .logging import log_database_operation as log_op
except ImportError:
    from .logging import log_operation as log_op


class ThemeRepo(GenericBaseRepository[ThemeORM]):
    """
    Repository for theme-related database operations.

    Handles CRUD operations for themes within dimensions
    with proper validation and error handling.
    """

    model = ThemeORM

    def __init__(self, session: Session):
        super().__init__(session)
        # Back-compat: some existing code references self.session / _handle_error
        self.session = self.s
        self._logger = logging.getLogger(__name__)

    # ----- internal error helper (back-compat with old BaseRepository) -----
    def _handle_error(self, exc: Exception, operation: str) -> None:
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

    @log_op("get_theme_by_name")
    def get_by_name(self, dimension_id: int, name: str) -> ThemeORM | None:
        """
        Get theme by dimension ID and name.
        """
        if dimension_id <= 0:
            raise ValidationError("dimension_id", "Dimension ID must be positive")
        if not name or not name.strip():
            raise ValidationError("name", "Theme name cannot be empty")

        try:
            return (
                self.session.query(ThemeORM)
                .filter_by(dimension_id=dimension_id, name=name.strip())
                .one_or_none()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "get_theme_by_name")

    @log_op("get_theme_by_id")
    def get_by_id(self, theme_id: int) -> ThemeORM | None:
        """
        Get theme by ID.
        """
        if theme_id <= 0:
            raise ValidationError("theme_id", "Theme ID must be positive")

        try:
            return self.session.get(ThemeORM, theme_id)
        except SQLAlchemyError as e:
            self._handle_error(e, "get_theme_by_id")

    @log_op("create_theme")
    def create(self, dimension_id: int, name: str) -> ThemeORM:
        """
        Create new theme.
        """
        # Validate input
        validated_data = ThemeInput(dimension_id=dimension_id, name=name)

        try:
            theme = ThemeORM(
                dimension_id=validated_data.dimension_id,
                name=validated_data.name,
            )
            self.session.add(theme)
            self.session.flush()
            return theme
        except SQLIntegrityError as e:
            self._handle_error(e, "create_theme")
        except SQLAlchemyError as e:
            self._handle_error(e, "create_theme")

    @log_op("list_themes_by_dimension")
    def list_by_dimension(self, dimension_id: int) -> list[ThemeORM]:
        """
        Get all themes for a dimension.
        """
        if dimension_id <= 0:
            raise ValidationError("dimension_id", "Dimension ID must be positive")

        try:
            return (
                self.session.query(ThemeORM)
                .filter_by(dimension_id=dimension_id)
                .order_by(ThemeORM.name)
                .all()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "list_themes_by_dimension")

    @log_op("list_themes_with_topics")
    def list_by_dimension_with_topics(self, dimension_id: int) -> list[ThemeORM]:
        """
        Get all themes for a dimension with eagerly loaded topics.
        """
        if dimension_id <= 0:
            raise ValidationError("dimension_id", "Dimension ID must be positive")

        try:
            return (
                self.session.query(ThemeORM)
                .options(joinedload(ThemeORM.topics))
                .filter_by(dimension_id=dimension_id)
                .order_by(ThemeORM.name)
                .all()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "list_themes_with_topics")
