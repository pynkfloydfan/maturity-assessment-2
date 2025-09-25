"""
Application API layer with comprehensive error handling and validation.

This module provides high-level functions for the assessment application
with proper error handling, user-friendly messages, and comprehensive logging.
"""

from __future__ import annotations

from decimal import Decimal
import json
import math
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from ..domain.schemas import (
    AssessmentEntryInput,
    SessionCombineInput,
    SessionCreationInput,
    validate_input,
)
from ..domain.services import AverageResult, ScoringService
from ..infrastructure.exceptions import (
    BusinessLogicError,
    ImportError,
    MultipleValidationError,
    ResilienceAssessmentError,
    TopicNotFoundError,
    ValidationError,
    create_user_friendly_error_message,
    log_error_details,
)
from ..infrastructure.logging import get_logger, log_operation, set_context
from ..infrastructure.models import (
    AssessmentEntryORM,
    AssessmentSessionORM,
    DimensionORM,
    ThemeORM,
    TopicORM,
)
from ..infrastructure.repositories import (
    EntryRepo,
    SessionRepo,
    TopicRepo,
)
from ..utils.resilience_radar import gradient_color, make_resilience_radar_with_theme_bars

logger = get_logger(__name__)


@log_operation("list_dimensions_with_topics")
def list_dimensions_with_topics(session: Session) -> pd.DataFrame:
    """
    Get comprehensive view of all dimensions, themes, and topics.

    Args:
        session: Database session

    Returns:
        DataFrame with columns: Dimension, Theme, TopicID, Topic

    Raises:
        DatabaseError: If database operation fails

    Example:
        >>> df = list_dimensions_with_topics(session)
        >>> print(df.head())
        >>> # Shows hierarchical structure of assessment framework
    """
    try:
        rows = (
            session.query(
                DimensionORM.name.label("Dimension"),
                ThemeORM.name.label("Theme"),
                TopicORM.id.label("TopicID"),
                TopicORM.name.label("Topic"),
            )
            .join(ThemeORM, ThemeORM.dimension_id == DimensionORM.id)
            .join(TopicORM, TopicORM.theme_id == ThemeORM.id)
            .order_by(DimensionORM.name, ThemeORM.name, TopicORM.name)
            .all()
        )

        df = pd.DataFrame(rows, columns=["Dimension", "Theme", "TopicID", "Topic"])
        logger.info(f"Retrieved {len(df)} topics across all dimensions")
        return df

    except Exception as e:
        error_details = log_error_details(e, {"operation": "list_dimensions_with_topics"})
        logger.error("Failed to list dimensions with topics", extra=error_details)
        raise ResilienceAssessmentError(
            "Failed to retrieve assessment structure",
            details=error_details,
            user_message="Unable to load assessment topics. Please try again.",
        ) from e


@log_operation("create_assessment_session")
def create_assessment_session(
    session: Session,
    name: str,
    assessor: str | None = None,
    organization: str | None = None,
    notes: str | None = None,
) -> AssessmentSessionORM:
    """
    Create a new assessment session with validation.

    Args:
        session: Database session
        name: Session name (required)
        assessor: Assessor name (optional)
        organization: Organization name (optional)
        notes: Session notes (optional)

    Returns:
        Created AssessmentSessionORM instance

    Raises:
        ValidationError: If input data is invalid
        IntegrityError: If session name already exists

    Example:
        >>> session_obj = create_assessment_session(
        ...     session,
        ...     "Q1 2024 Assessment",
        ...     "John Smith",
        ...     "ACME Corp",
        ...     "Initial maturity baseline"
        ... )
        >>> print(f"Created session: {session_obj.id}")
    """
    # Validate input
    validation_result = validate_input(
        SessionCreationInput,
        {"name": name, "assessor": assessor, "organization": organization, "notes": notes},
    )

    if not validation_result.success:
        error_msg = "; ".join([f"{e.field}: {e.message}" for e in validation_result.errors])
        logger.warning(f"Session creation validation failed: {error_msg}")
        raise ValidationError("session_data", error_msg)

    validated_data = validation_result.data
    if validated_data is None:
        raise RuntimeError("Validation succeeded but returned no data")

    try:
        set_context(operation="create_session", session_name=name)
        repo = SessionRepo(session)
        session_obj = repo.create(
            name=validated_data["name"],
            assessor=validated_data["assessor"],
            organization=validated_data["organization"],
            notes=validated_data["notes"],
        )

        logger.info(f"Created assessment session '{name}' with ID {session_obj.id}")
        return session_obj

    except Exception as e:
        error_details = log_error_details(e, {"session_name": name})
        logger.error("Failed to create assessment session", extra=error_details)

        # Re-raise custom exceptions as-is
        if isinstance(e, ResilienceAssessmentError):
            raise

        # Convert generic errors
        raise ResilienceAssessmentError(
            f"Failed to create session '{name}': {str(e)}",
            details=error_details,
            user_message=create_user_friendly_error_message(e),
        ) from e


@log_operation("record_topic_rating")
def record_topic_rating(
    session: Session,
    session_id: int,
    topic_id: int,
    rating_level: int | None = None,
    is_na: bool = False,
    comment: str | None = None,
) -> AssessmentEntryORM:
    """
    Record or update a topic rating with comprehensive validation.

    Args:
        session: Database session
        session_id: Target assessment session ID
        topic_id: Topic being rated
        rating_level: CMMI rating (1-5) or None if N/A
        is_na: Whether this entry is marked as Not Applicable
        comment: Optional comment for the rating

    Returns:
        AssessmentEntryORM instance

    Raises:
        ValidationError: If input data is invalid
        SessionNotFoundError: If session doesn't exist
        TopicNotFoundError: If topic doesn't exist

    Example:
        >>> entry = record_topic_rating(
        ...     session,
        ...     session_id=1,
        ...     topic_id=123,
        ...     rating_level=3,
        ...     comment="Good practices in place"
        ... )
        >>> print(f"Recorded rating: {entry.rating_level}")
    """
    # Validate input
    validation_result = validate_input(
        AssessmentEntryInput,
        {
            "session_id": session_id,
            "topic_id": topic_id,
            "rating_level": rating_level,
            "is_na": is_na,
            "comment": comment,
        },
    )

    if not validation_result.success:
        error_msg = "; ".join([f"{e.field}: {e.message}" for e in validation_result.errors])
        logger.warning(f"Rating validation failed: {error_msg}")
        raise ValidationError("rating_data", error_msg)

    try:
        set_context(operation="record_rating", session_id=session_id, topic_id=topic_id)

        # Verify session exists
        session_repo = SessionRepo(session)
        session_repo.get_by_id_required(session_id)

        # Verify topic exists
        topic_repo = TopicRepo(session)
        topic_repo.get_by_id_required(topic_id)

        # Record the rating
        entry_repo = EntryRepo(session)
        entry = entry_repo.upsert(
            session_id=session_id,
            topic_id=topic_id,
            rating_level=rating_level,
            is_na=is_na,
            comment=comment,
        )

        rating_desc = "N/A" if is_na else f"Level {rating_level}"
        logger.info(f"Recorded rating {rating_desc} for topic {topic_id} in session {session_id}")
        return entry

    except Exception as e:
        error_details = log_error_details(
            e, {"session_id": session_id, "topic_id": topic_id, "rating_level": rating_level}
        )
        logger.error("Failed to record topic rating", extra=error_details)

        # Re-raise custom exceptions as-is
        if isinstance(e, ResilienceAssessmentError):
            raise

        # Convert generic errors
        raise ResilienceAssessmentError(
            f"Failed to record rating for topic {topic_id}: {str(e)}",
            details=error_details,
            user_message=create_user_friendly_error_message(e),
        ) from e


@log_operation("compute_theme_averages")
def compute_theme_averages(session: Session, session_id: int) -> list[AverageResult]:
    """
    Compute average scores per theme for a session.

    Args:
        session: Database session
        session_id: Assessment session ID

    Returns:
        List of theme averages with coverage information

    Raises:
        SessionNotFoundError: If session doesn't exist
        DatabaseError: If calculation fails

    Example:
        >>> averages = compute_theme_averages(session, session_id=1)
        >>> for avg in averages:
        ...     print(f"Theme: {avg['name']}, Score: {avg['average']:.2f}")
    """
    try:
        set_context(operation="compute_theme_averages", session_id=session_id)

        # Verify session exists
        session_repo = SessionRepo(session)
        session_repo.get_by_id_required(session_id)

        # Calculate averages
        scoring_service = ScoringService(session)
        results = scoring_service.compute_theme_averages(session_id)

        # Guard: ensure we return AverageResult objects internally (UI expects attributes)
        from app.domain.services import AverageResult  # adjust path if needed

        assert all(
            isinstance(r, AverageResult) for r in results
        ), "API must return List[AverageResult]; do not convert to dicts here."

        # # Convert to dict format for easy consumption. DO NOT use as breaks the app
        # # Consider adding convert_to_dict() method to AverageResult if needed
        # averages = []
        # for result in results:
        #     averages.append({
        #         "id": result.id,
        #         "name": result.name,
        #         "average": result.average,
        #         "coverage": result.coverage,
        #         "coverage_percent": round(result.coverage * 100, 1)
        #     })

        logger.info(f"Computed averages for {len(results)} themes in session {session_id}")
        return results

    except Exception as e:
        error_details = log_error_details(e, {"session_id": session_id})
        logger.error("Failed to compute theme averages", extra=error_details)

        if isinstance(e, ResilienceAssessmentError):
            raise

        raise ResilienceAssessmentError(
            f"Failed to calculate theme averages for session {session_id}: {str(e)}",
            details=error_details,
            user_message="Unable to calculate theme scores. Please try again.",
        ) from e


@log_operation("compute_dimension_averages")
def compute_dimension_averages(session: Session, session_id: int) -> list[AverageResult]:
    """
    Compute average scores per dimension for a session.

    Args:
        session: Database session
        session_id: Assessment session ID

    Returns:
        List of dimension averages with coverage information

    Raises:
        SessionNotFoundError: If session doesn't exist
        DatabaseError: If calculation fails

    Example:
        >>> averages = compute_dimension_averages(session, session_id=1)
        >>> for avg in averages:
        ...     print(f"Dimension: {avg['name']}, Score: {avg['average']:.2f}")
    """
    try:
        set_context(operation="compute_dimension_averages", session_id=session_id)

        # Verify session exists
        session_repo = SessionRepo(session)
        session_repo.get_by_id_required(session_id)

        # Calculate averages
        scoring_service = ScoringService(session)
        results = scoring_service.compute_dimension_averages(session_id)

        # Guard: ensure we return AverageResult objects internally (UI expects attributes)
        from app.domain.services import AverageResult  # adjust path if needed

        assert all(
            isinstance(r, AverageResult) for r in results
        ), "API must return List[AverageResult]; do not convert to dicts here."

        # # Convert to dict format. DO NOT Use as breaks the app
        # Consider adding convert_to_dict() method to AverageResult if needed
        # averages = []
        # for result in results:
        #     averages.append({
        #         "id": result.id,
        #         "name": result.name,
        #         "average": result.average,
        #         "coverage": result.coverage,
        #         "coverage_percent": round(result.coverage * 100, 1)
        #     })

        logger.info(f"Computed averages for {len(results)} dimensions in session {session_id}")
        return results

    except Exception as e:
        error_details = log_error_details(e, {"session_id": session_id})
        logger.error("Failed to compute dimension averages", extra=error_details)

        if isinstance(e, ResilienceAssessmentError):
            raise

        raise ResilienceAssessmentError(
            f"Failed to calculate dimension averages for session {session_id}: {str(e)}",
            details=error_details,
            user_message="Unable to calculate dimension scores. Please try again.",
        ) from e


@log_operation("build_dashboard_figures")
def build_dashboard_figures(session: Session, session_id: int) -> dict[str, Any]:
    """Create Plotly-ready dashboard payload (dimension tiles + radar figure)."""

    try:
        set_context(operation="build_dashboard_figures", session_id=session_id)

        # Ensure session exists
        session_repo = SessionRepo(session)
        session_repo.get_by_id_required(session_id)

        # Dimension tiles (average + colour)
        dimension_results = compute_dimension_averages(session, session_id=session_id)
        tiles = []
        for result in dimension_results:
            avg_value = None
            colour = None
            if result.average is not None and not math.isnan(result.average):
                avg_value = float(result.average)
                colour = gradient_color(avg_value)
            tiles.append(
                {
                    "id": result.id,
                    "name": result.name,
                    "average": avg_value,
                    "coverage": float(result.coverage) if result.coverage is not None else None,
                    "color": colour,
                }
            )

        # Radar figure requires score rows per topic
        radar_json: dict[str, Any] | None = None
        topics_df = list_dimensions_with_topics(session)
        entries = (
            session.query(AssessmentEntryORM)
            .filter(AssessmentEntryORM.session_id == session_id)
            .all()
        )

        ratings_map: dict[int, float] = {}
        for entry in entries:
            if entry.is_na:
                continue
            if entry.computed_score is not None:
                ratings_map[entry.topic_id] = float(entry.computed_score)
            elif entry.rating_level is not None:
                ratings_map[entry.topic_id] = float(entry.rating_level)

        score_rows: list[dict[str, Any]] = []
        for _, row in topics_df.iterrows():
            topic_id = int(row["TopicID"])
            score = ratings_map.get(topic_id)
            if score is None:
                continue
            score_rows.append(
                {
                    "Dimension": row["Dimension"],
                    "Theme": row["Theme"],
                    "Question": row["Topic"],
                    "Score": score,
                }
            )

        if score_rows:
            scores_df = pd.DataFrame(score_rows, columns=["Dimension", "Theme", "Question", "Score"])
            figure = make_resilience_radar_with_theme_bars(scores_df)
            radar_json = json.loads(figure.to_json())

        return {"tiles": tiles, "radar": radar_json}

    except Exception as e:  # pragma: no cover - bubbled as API error
        error_details = log_error_details(e, {"session_id": session_id})
        logger.error("Failed to build dashboard figures", extra=error_details)

        if isinstance(e, ResilienceAssessmentError):
            raise

        raise ResilienceAssessmentError(
            f"Failed to build dashboard for session {session_id}: {str(e)}",
            details=error_details,
            user_message="Unable to build dashboard visuals. Please try again.",
        ) from e


@log_operation("export_session_results")
def export_session_results(session: Session, session_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Export session results as DataFrames for download/analysis.

    Args:
        session: Database session
        session_id: Assessment session ID

    Returns:
        Tuple of (topics_df, entries_df) DataFrames

    Raises:
        SessionNotFoundError: If session doesn't exist
        ExportError: If export operation fails

    Example:
        >>> topics_df, entries_df = export_session_results(session, session_id=1)
        >>> # topics_df contains the assessment structure
        >>> # entries_df contains all ratings and comments
    """
    try:
        set_context(operation="export_results", session_id=session_id)

        # Verify session exists
        session_repo = SessionRepo(session)
        session_repo.get_by_id_required(session_id)

        # Get topics structure
        topics_df = list_dimensions_with_topics(session)

        # Get session entries
        entry_repo = EntryRepo(session)
        entries = entry_repo.list_for_session(session_id)

        # Convert entries to DataFrame
        entry_rows = []
        for entry in entries:
            entry_rows.append(
                {
                    "TopicID": entry.topic_id,
                    "Rating": entry.rating_level,
                    "ComputedScore": float(entry.computed_score) if entry.computed_score else None,
                    "N/A": entry.is_na,
                    "Comment": entry.comment,
                    "CreatedAt": entry.created_at,
                }
            )

        entries_df = (
            pd.DataFrame(entry_rows)
            if entry_rows
            else pd.DataFrame(
                columns=["TopicID", "Rating", "ComputedScore", "N/A", "Comment", "CreatedAt"]
            )
        )

        logger.info(f"Exported {len(entries_df)} entries for session {session_id}")
        return topics_df, entries_df

    except Exception as e:
        error_details = log_error_details(e, {"session_id": session_id})
        logger.error("Failed to export session results", extra=error_details)

        if isinstance(e, ResilienceAssessmentError):
            raise

        from ..infrastructure.exceptions import ExportError

        raise ExportError(
            f"Failed to export results for session {session_id}: {str(e)}", details=error_details
        ) from e


@log_operation("import_session_results")
def import_session_results(
    session: Session,
    session_id: int,
    dataframe: pd.DataFrame,
) -> int:
    """Import assessment entries for a session from a DataFrame."""

    try:
        set_context(operation="import_results", session_id=session_id)

        session_repo = SessionRepo(session)
        session_repo.get_by_id_required(session_id)

        if dataframe is None or dataframe.empty:
            logger.info("No rows provided for import; skipping")
            return 0

        topic_repo = TopicRepo(session)
        entry_repo = EntryRepo(session)

        records = dataframe.to_dict(orient="records")
        validation_errors: list[ValidationError] = []
        processed = 0

        def _is_missing(value: Any) -> bool:
            if value is None or value is pd.NA:
                return True
            if isinstance(value, float) and math.isnan(value):
                return True
            if isinstance(value, str) and not value.strip():
                return True
            return False

        for index, row in enumerate(records, start=2):
            topic_id_raw = row.get("TopicID")
            if _is_missing(topic_id_raw):
                continue

            try:
                topic_id = int(topic_id_raw)
                topic_repo.get_by_id_required(topic_id)
            except (ValueError, TopicNotFoundError, ValidationError) as exc:
                validation_errors.append(
                    ValidationError(
                        "TopicID",
                        f"Invalid topic reference at row {index}",
                        value=topic_id_raw,
                        details={"row": index, "error": str(exc)},
                    )
                )
                continue

            rating_raw = row.get("Rating")
            rating_level: int | None
            if _is_missing(rating_raw):
                rating_level = None
            else:
                try:
                    rating_level = int(float(rating_raw))
                except (TypeError, ValueError):
                    validation_errors.append(
                        ValidationError(
                            "Rating",
                            f"Invalid rating value at row {index}",
                            value=rating_raw,
                            details={"row": index},
                        )
                    )
                    continue

            computed_raw = row.get("ComputedScore")
            if _is_missing(computed_raw):
                computed_score = None
            else:
                try:
                    computed_score = Decimal(str(computed_raw))
                except (ValueError, ArithmeticError):
                    validation_errors.append(
                        ValidationError(
                            "ComputedScore",
                            f"Invalid computed score at row {index}",
                            value=computed_raw,
                            details={"row": index},
                        )
                    )
                    continue

            na_raw = row.get("N/A")
            is_na = False
            if not _is_missing(na_raw):
                if isinstance(na_raw, str):
                    is_na = na_raw.strip().lower() in {"1", "true", "yes", "y"}
                else:
                    is_na = bool(na_raw)

            comment_raw = row.get("Comment")
            comment = None if _is_missing(comment_raw) else str(comment_raw).strip()

            if not any([rating_level is not None, is_na, comment, computed_score is not None]):
                continue

            try:
                entry_repo.upsert(
                    session_id=session_id,
                    topic_id=topic_id,
                    rating_level=rating_level,
                    computed_score=computed_score,
                    is_na=is_na,
                    comment=comment,
                )
                processed += 1
            except ValidationError as exc:
                validation_errors.append(
                    ValidationError(
                        exc.field,
                        f"Row {index}: {exc.message}",
                        value=exc.value,
                        details={"row": index, **exc.details},
                    )
                )

        if validation_errors:
            raise MultipleValidationError(validation_errors)

        logger.info("Imported %s entries for session %s", processed, session_id)
        return processed

    except ResilienceAssessmentError:
        raise
    except MultipleValidationError:
        raise
    except Exception as e:
        error_details = log_error_details(e, {"session_id": session_id})
        logger.error("Failed to import session results", extra=error_details)
        raise ImportError(
            f"Failed to import results for session {session_id}: {str(e)}",
            details=error_details,
        ) from e

@log_operation("combine_sessions")
def combine_sessions_to_master(
    session: Session,
    source_session_ids: list[int],
    name: str,
    assessor: str | None = None,
    organization: str | None = None,
    notes: str | None = None,
) -> AssessmentSessionORM:
    """
    Create a master session by combining multiple source sessions.

    Averages topic scores across the selected source sessions, excluding N/A entries.
    Uses computed_score (decimal) to preserve precision. Topics with no ratings
    across all sources are marked N/A.

    Args:
        session: Database session
        source_session_ids: List of session IDs to combine
        name: Name for the new master session
        assessor: Assessor for the master session (optional)
        organization: Organization for the master session (optional)
        notes: Notes for the master session (optional)

    Returns:
        Created master AssessmentSessionORM instance

    Raises:
        ValidationError: If input data is invalid
        SessionNotFoundError: If any source session doesn't exist
        BusinessLogicError: If combination logic fails

    Example:
        >>> master = combine_sessions_to_master(
        ...     session,
        ...     [1, 2, 3],
        ...     "Combined Q1-Q3 Assessment",
        ...     "Assessment Team",
        ...     "ACME Corp",
        ...     "Quarterly combined results"
        ... )
        >>> print(f"Created master session: {master.id}")
    """
    # Validate input
    validation_result = validate_input(
        SessionCombineInput,
        {
            "source_session_ids": source_session_ids,
            "name": name,
            "assessor": assessor,
            "organization": organization,
            "notes": notes,
        },
    )

    if not validation_result.success:
        error_msg = "; ".join([f"{e.field}: {e.message}" for e in validation_result.errors])
        logger.warning(f"Session combination validation failed: {error_msg}")
        raise ValidationError("combination_data", error_msg)

    try:
        set_context(
            operation="combine_sessions", source_sessions=source_session_ids, master_name=name
        )

        # Verify all source sessions exist
        session_repo = SessionRepo(session)
        for sid in source_session_ids:
            session_repo.get_by_id_required(sid)

        # Create master session
        master = create_assessment_session(
            session, name=name, assessor=assessor, organization=organization, notes=notes
        )

        # Get all topics
        topic_repo = TopicRepo(session)
        all_topics = topic_repo.list_all()

        if not all_topics:
            raise BusinessLogicError(
                "No topics found in the system", rule="topics_required_for_combination"
            )

        # Index entries by topic across source sessions
        from collections import defaultdict

        by_topic: dict[int, list[float]] = defaultdict(list)

        entry_repo = EntryRepo(session)
        for session_id in source_session_ids:
            entries = entry_repo.list_for_session(session_id)
            for entry in entries:
                if entry.is_na:
                    continue

                # Use computed_score if available, otherwise rating_level
                value = (
                    entry.computed_score if entry.computed_score is not None else entry.rating_level
                )
                if value is not None:
                    by_topic[entry.topic_id].append(float(value))

        # Create master entries
        entries_created = 0
        entries_na = 0

        for topic in all_topics:
            values = by_topic.get(topic.id, [])

            if values:
                # Calculate average
                average_score = sum(values) / len(values)

                entry_repo.upsert(
                    session_id=master.id,
                    topic_id=topic.id,
                    rating_level=None,
                    computed_score=Decimal(str(round(average_score, 2))),
                    is_na=False,
                    comment=(
                        f"Combined from {len(values)} ratings across "
                        f"{len(source_session_ids)} sessions"
                    ),
                )
                entries_created += 1
            else:
                # No ratings for this topic across any source session
                entry_repo.upsert(
                    session_id=master.id,
                    topic_id=topic.id,
                    rating_level=None,
                    computed_score=None,
                    is_na=True,
                    comment="No ratings available in source sessions",
                )
                entries_na += 1

        session.flush()

        logger.info(
            f"Combined {len(source_session_ids)} sessions into master session {master.id}: "
            f"{entries_created} calculated entries, {entries_na} N/A entries"
        )

        return master

    except Exception as e:
        error_details = log_error_details(
            e, {"source_sessions": source_session_ids, "master_name": name}
        )
        logger.error("Failed to combine sessions", extra=error_details)

        if isinstance(e, ResilienceAssessmentError):
            raise

        raise BusinessLogicError(
            f"Failed to combine sessions into '{name}': {str(e)}",
            rule="session_combination",
            details=error_details,
        ) from e


@log_operation("get_session_summary")
def get_session_summary(session: Session, session_id: int) -> dict[str, Any]:
    """
    Get comprehensive summary of an assessment session.

    Args:
        session: Database session
        session_id: Assessment session ID

    Returns:
        Dictionary with session details and statistics

    Raises:
        SessionNotFoundError: If session doesn't exist

    Example:
        >>> summary = get_session_summary(session, session_id=1)
        >>> print(f"Session: {summary['name']}")
        >>> print(f"Progress: {summary['completion_percent']:.1f}%")
    """
    try:
        set_context(operation="get_summary", session_id=session_id)

        # Get session details
        session_repo = SessionRepo(session)
        session_obj = session_repo.get_by_id_required(session_id)

        # Get entries
        entry_repo = EntryRepo(session)
        entries = entry_repo.list_for_session(session_id)

        # Get total topics count
        topic_repo = TopicRepo(session)
        total_topics = len(topic_repo.list_all())

        # Calculate statistics
        total_entries = len(entries)
        rated_entries = len([e for e in entries if not e.is_na and e.rating_level is not None])
        na_entries = len([e for e in entries if e.is_na])
        computed_entries = len([e for e in entries if e.computed_score is not None])

        completion_percent = (total_entries / total_topics * 100) if total_topics > 0 else 0
        rating_percent = (rated_entries / total_entries * 100) if total_entries > 0 else 0

        summary = {
            "id": session_obj.id,
            "name": session_obj.name,
            "assessor": session_obj.assessor,
            "organization": session_obj.organization,
            "notes": session_obj.notes,
            "created_at": session_obj.created_at,
            "statistics": {
                "total_topics": total_topics,
                "total_entries": total_entries,
                "rated_entries": rated_entries,
                "na_entries": na_entries,
                "computed_entries": computed_entries,
                "completion_percent": round(completion_percent, 1),
                "rating_percent": round(rating_percent, 1),
            },
        }

        logger.info(
            f"Generated summary for session {session_id}: {completion_percent:.1f}% complete"
        )
        return summary

    except Exception as e:
        error_details = log_error_details(e, {"session_id": session_id})
        logger.error("Failed to get session summary", extra=error_details)

        if isinstance(e, ResilienceAssessmentError):
            raise

        raise ResilienceAssessmentError(
            f"Failed to get summary for session {session_id}: {str(e)}",
            details=error_details,
            user_message="Unable to load session summary. Please try again.",
        ) from e

