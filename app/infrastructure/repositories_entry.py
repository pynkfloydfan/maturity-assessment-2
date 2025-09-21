# app/infrastructure/repositories_entry.py
from __future__ import annotations

import logging
from decimal import Decimal
from typing import NoReturn

from sqlalchemy.exc import IntegrityError as SQLIntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

# Prefer sibling package path for schemas (app/domain/schemas.py)
from ..domain.schemas import AssessmentEntryInput

# Validation schema and app exceptions
from .exceptions import ValidationError
from .models import AssessmentEntryORM, TopicORM

# Use the generic base (typed) — alias to avoid any name collision elsewhere
from .repositories_base import BaseRepository as GenericBaseRepository

# Logging decorator(s)
try:
    from .logging import log_database_operation as log_op
except ImportError:
    from .logging import log_operation as log_op


class EntryRepo(GenericBaseRepository[AssessmentEntryORM]):
    """
    Repository for assessment entry database operations.

    Handles CRUD operations for individual topic ratings within sessions
    with proper validation and error handling.
    """

    model = AssessmentEntryORM

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

    @log_op("upsert_entry")
    def upsert(
        self,
        session_id: int,
        topic_id: int,
        rating_level: int | None = None,
        computed_score: Decimal | None = None,
        is_na: bool = False,
        comment: str | None = None,
    ) -> AssessmentEntryORM:
        """
        Create or update assessment entry.
        """
        # Validate input using schema
        validated_data = AssessmentEntryInput(
            session_id=session_id,
            topic_id=topic_id,
            rating_level=rating_level,
            computed_score=computed_score,
            is_na=is_na,
            comment=comment,
        )

        try:
            obj = (
                self.session.query(AssessmentEntryORM)
                .filter_by(session_id=session_id, topic_id=topic_id)
                .one_or_none()
            )

            if obj is None:
                obj = AssessmentEntryORM(session_id=session_id, topic_id=topic_id)
                self.session.add(obj)

            # Update fields
            obj.rating_level = validated_data.rating_level
            obj.computed_score = (
                float(validated_data.computed_score)
                if validated_data.computed_score is not None
                else None
            )
            obj.is_na = validated_data.is_na
            obj.comment = validated_data.comment

            self.session.flush()
            return obj

        except SQLIntegrityError as e:
            self._handle_error(e, "upsert_entry")
        except SQLAlchemyError as e:
            self._handle_error(e, "upsert_entry")

    @log_op("list_entries_for_session")
    def list_for_session(self, session_id: int) -> list[AssessmentEntryORM]:
        """
        Get all entries for a session.
        """
        if session_id <= 0:
            raise ValidationError("session_id", "Session ID must be positive")

        try:
            return (
                self.session.query(AssessmentEntryORM)
                .filter_by(session_id=session_id)
                .join(TopicORM)
                .order_by(TopicORM.name)
                .all()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "list_entries_for_session")

    @log_op("get_entry")
    def get_by_session_and_topic(self, session_id: int, topic_id: int) -> AssessmentEntryORM | None:
        """
        Get specific entry by session and topic ID.
        """
        if session_id <= 0:
            raise ValidationError("session_id", "Session ID must be positive")
        if topic_id <= 0:
            raise ValidationError("topic_id", "Topic ID must be positive")

        try:
            return (
                self.session.query(AssessmentEntryORM)
                .filter_by(session_id=session_id, topic_id=topic_id)
                .one_or_none()
            )
        except SQLAlchemyError as e:
            self._handle_error(e, "get_entry")

    @log_op("delete_entry")
    def delete_by_session_and_topic(self, session_id: int, topic_id: int) -> bool:
        """
        Delete specific entry by session and topic ID.
        """
        entry = self.get_by_session_and_topic(session_id, topic_id)
        if entry is None:
            return False

        try:
            self.session.delete(entry)
            self.session.flush()
            return True
        except SQLAlchemyError as e:
            self._handle_error(e, "delete_entry")
