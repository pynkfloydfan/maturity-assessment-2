# app/infrastructure/repositories_topic.py
from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError as SQLIntegrityError, SQLAlchemyError
from sqlalchemy.orm import (
    Session,
)  # joinedload not used here but OK if you add a variant

# TopicInput path: prefer sibling package "domain.schemas"
from ..domain.schemas import TopicInput  # app/domain/schemas.py

# Validation schema and app exceptions
from .exceptions import TopicNotFoundError, ValidationError
from .models import DimensionORM, ThemeORM, TopicORM

# Use the generic base (typed) — alias to avoid any name collision elsewhere
from .repositories_base import BaseRepository as GenericBaseRepository

# Logging decorator(s)
try:
    from .logging import log_database_operation as log_op
except ImportError:
    from .logging import log_operation as log_op


class TopicRepo(GenericBaseRepository[TopicORM]):
    """
    Repository for topic-related database operations.

    Handles CRUD operations for assessment topics within themes
    with proper validation and error handling.
    """

    model = TopicORM

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

    @log_op("get_topic_by_name")
    def get_by_name(self, theme_id: int, name: str) -> TopicORM | None:
        """
        Get topic by theme ID and name.
        """
        if theme_id <= 0:
            raise ValidationError("theme_id", "Theme ID must be positive")
        if not name or not name.strip():
            raise ValidationError("name", "Topic name cannot be empty")

        try:
            return (
                self.session.query(TopicORM)
                .filter_by(theme_id=theme_id, name=name.strip())
                .one_or_none()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "get_topic_by_name")

    @log_op("get_topic_by_id")
    def get_by_id(self, topic_id: int) -> TopicORM | None:
        """
        Get topic by ID.
        """
        if topic_id <= 0:
            raise ValidationError("topic_id", "Topic ID must be positive")

        try:
            return self.session.get(TopicORM, topic_id)
        except SQLAlchemyError as e:
            self._handle_error(e, "get_topic_by_id")

    def get_by_id_required(self, topic_id: int) -> TopicORM:
        """
        Get topic by ID, raising exception if not found.
        """
        topic = self.get_by_id(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)
        return topic

    @log_op("create_topic")
    def create(self, theme_id: int, name: str) -> TopicORM:
        """
        Create new topic.
        """
        # Validate input
        validated_data = TopicInput(theme_id=theme_id, name=name)

        try:
            topic = TopicORM(
                theme_id=validated_data.theme_id,
                name=validated_data.name,
            )
            self.session.add(topic)
            self.session.flush()
            return topic
        except SQLIntegrityError as e:
            self._handle_error(e, "create_topic")
        except SQLAlchemyError as e:
            self._handle_error(e, "create_topic")

    @log_op("list_topics_by_theme")
    def list_by_theme(self, theme_id: int) -> list[TopicORM]:
        """
        Get all topics for a theme.
        """
        if theme_id <= 0:
            raise ValidationError("theme_id", "Theme ID must be positive")

        try:
            return (
                self.session.query(TopicORM)
                .filter_by(theme_id=theme_id)
                .order_by(TopicORM.name)
                .all()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "list_topics_by_theme")

    @log_op("list_all_topics")
    def list_all(self) -> list[TopicORM]:
        """
        Get all topics across all themes.
        """
        try:
            return (
                self.session.query(TopicORM)
                .join(ThemeORM)
                .join(DimensionORM)
                .order_by(DimensionORM.name, ThemeORM.name, TopicORM.name)
                .all()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "list_all_topics")
