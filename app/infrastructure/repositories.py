"""
Improved repository classes with comprehensive validation, error handling, and logging.

This module provides data access layer implementations with:
- Pydantic validation for all inputs
- Structured error handling with custom exceptions
- Comprehensive logging and monitoring
- Optimized database queries with eager loading
- Consistent patterns across all repositories
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError as SQLIntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .exceptions import (
    ValidationError,
    handle_database_error,
)
from .logging import get_logger, log_database_operation
from .models import (
    ExplanationORM,
)
from .repositories_dimension import DimensionRepo  # re-export
from .repositories_entry import EntryRepo
from .repositories_ratingscale import RatingScaleRepo  # re-export

# Re-export split repositories so existing imports keep working:
#   from app.infrastructure.repositories import SessionRepo, ...
from .repositories_session import SessionRepo  # re-export
from .repositories_theme import ThemeRepo  # re-export
from .repositories_topic import TopicRepo  # re-export

# Tell linters/formatters these imports are intentional (exported API)
__all__ = [
    "SessionRepo",
    "DimensionRepo",
    "ThemeRepo",
    "TopicRepo",
    "RatingScaleRepo",
    "EntryRepo",
]


class BaseRepository:
    """
    Base repository class with common functionality and error handling.

    Provides consistent patterns for database operations, error handling,
    and logging across all repository classes.

    Example:
        >>> repo = DimensionRepo(session)
        >>> dimensions = repo.list()
    """

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session instance
        """
        self.session = session
        self.logger = get_logger(self.__class__.__name__)

    def _handle_error(self, error: Exception, operation: str) -> None:
        """
        Convert database errors to application-specific exceptions.

        Args:
            error: Original database error
            operation: Description of the operation that failed

        Raises:
            Appropriate application exception
        """
        db_error = handle_database_error(error, operation)
        self.logger.error(f"Database error in {operation}: {str(error)}", exc_info=True)
        raise db_error


class ExplanationRepo(BaseRepository):
    """
    Repository for explanation-related database operations.

    Handles CRUD operations for topic-level explanations
    with proper validation and error handling.

    Example:
        >>> repo = ExplanationRepo(session)
        >>> explanations = repo.list_for_topic(topic_id=123)
        >>> for exp in explanations:
        ...     print(f"Level {exp.level}: {exp.text[:50]}...")
    """

    @log_database_operation("create_explanation")
    def create(self, topic_id: int, level: int, text: str) -> ExplanationORM:
        """
        Create new explanation.

        Args:
            topic_id: Parent topic ID
            level: CMMI level this explanation applies to
            text: Explanation text

        Returns:
            Created ExplanationORM instance
        """
        # Validate input using schema
        from ..domain.schemas import ExplanationInput

        validated_data = ExplanationInput(topic_id=topic_id, level=level, text=text)

        try:
            explanation = ExplanationORM(
                topic_id=validated_data.topic_id,
                level=validated_data.level,
                text=validated_data.text,
            )
            self.session.add(explanation)
            self.session.flush()
            return explanation
        except SQLIntegrityError as e:
            self._handle_error(e, "create_explanation")
        except SQLAlchemyError as e:
            self._handle_error(e, "create_explanation")

    @log_database_operation("list_explanations_for_topic")
    def list_for_topic(self, topic_id: int) -> list[ExplanationORM]:
        """
        Get all explanations for a topic.

        Args:
            topic_id: Topic ID to filter by

        Returns:
            List of ExplanationORM instances ordered by level
        """
        if topic_id <= 0:
            raise ValidationError("topic_id", "Topic ID must be positive")

        try:
            return (
                self.session.query(ExplanationORM)
                .filter_by(topic_id=topic_id)
                .order_by(ExplanationORM.level, ExplanationORM.id)
                .all()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "list_explanations_for_topic")
