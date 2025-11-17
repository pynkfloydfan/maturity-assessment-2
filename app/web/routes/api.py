from __future__ import annotations

import io
import json
import logging
import math
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.application import api as app_api
from app.infrastructure.config import DatabaseConfig
from app.infrastructure.db import create_database_engine, create_session_factory
from app.infrastructure.exceptions import (
    MultipleValidationError,
    ResilienceAssessmentError,
    SessionNotFoundError,
)
from app.infrastructure.models import (
    AssessmentEntryORM,
    DimensionORM,
    ExplanationORM,
    RatingScaleORM,
    ThemeLevelGuidanceORM,
    ThemeORM,
    TopicORM,
)
from app.infrastructure.repositories import SessionRepo
from app.utils.exports import make_json_export_payload, make_xlsx_export_bytes
from app.utils.seed import initialise_database, seed_database_from_excel
from app.web.dependencies import get_db_config, get_db_session
from app.web.schemas import (
    AcronymResponse,
    AverageScore,
    DashboardData,
    DashboardFiguresResponse,
    DatabaseInitRequest,
    DatabaseOperationResponse,
    DatabaseSettings,
    Dimension,
    DimensionAssessmentResponse,
    ProgressSummary,
    RatingBulkUpdateRequest,
    RatingScale,
    RatingUpdate,
    SeedRequest,
    SeedResponse,
    ImportResponse,
    SessionCombineRequest,
    SessionCreateRequest,
    SessionDetail,
    SessionListItem,
    SessionSummary,
    SessionStatistics,
    Theme,
    ThemeAssessmentBlock,
    ThemeLevelGuidance,
    ThemeAverageScore,
    ThemeTopicsResponse,
    TopicAssessmentDetail,
    TopicDetail,
    TopicScore,
)

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = APP_DIR.parent
DEFAULT_EXCEL_PATH = (APP_DIR / "source_data" / "Maturity_Assessment_Data.xlsx").resolve()


def _config_to_dict(config: DatabaseConfig) -> dict[str, object]:
    if hasattr(config, "model_dump"):
        return config.model_dump()  # type: ignore[no-any-return]
    return config.dict()  # type: ignore[no-any-return]


def _config_to_schema(config: DatabaseConfig) -> DatabaseSettings:
    return DatabaseSettings(
        backend=config.backend,
        sqlite_path=config.sqlite_path,
        mysql_host=config.mysql_host,
        mysql_port=config.mysql_port,
        mysql_user=config.mysql_user,
        mysql_database=config.mysql_database,
    )


def _merge_config(request: Request, payload: DatabaseInitRequest | None) -> DatabaseConfig:
    base_config = get_db_config(request)
    if payload is None:
        return base_config

    data = _config_to_dict(base_config)

    if payload.backend is not None:
        data["backend"] = payload.backend

    backend = data.get("backend", base_config.backend)

    if backend == "sqlite":
        if payload.sqlite_path is not None:
            data["sqlite_path"] = payload.sqlite_path
    else:
        if payload.sqlite_path is not None:
            data["sqlite_path"] = payload.sqlite_path
        for attr in [
            "mysql_host",
            "mysql_port",
            "mysql_user",
            "mysql_password",
            "mysql_database",
        ]:
            value = getattr(payload, attr)
            if value is not None:
                data[attr] = value

    return DatabaseConfig(**data)


def _store_runtime_config(
    request: Request,
    config: DatabaseConfig,
    engine: Engine | None = None,
) -> None:
    if engine is None:
        engine = create_database_engine(config)
    session_factory = create_session_factory(engine)
    config_dict = _config_to_dict(config)

    request.app.state.db_config = config
    request.app.state.db_engine = engine
    request.app.state.session_factory = session_factory
    request.app.state.session_factory_config = config_dict


def _safe_average(value: float | None) -> float | None:
    if value is None:
        return None
    if math.isnan(value):
        return None
    return float(value)


@router.get("/settings/database", response_model=DatabaseSettings)
def get_database_settings_endpoint(request: Request) -> DatabaseSettings:
    config = get_db_config(request)
    return _config_to_schema(config)


@router.put("/settings/database", response_model=DatabaseSettings)
def update_database_settings(
    payload: DatabaseInitRequest,
    request: Request,
) -> DatabaseSettings:
    config = _merge_config(request, payload)
    _store_runtime_config(request, config)
    return _config_to_schema(config)


@router.post("/settings/database/init", response_model=DatabaseOperationResponse)
def initialise_database_endpoint(
    request: Request,
    payload: DatabaseInitRequest | None = None,
) -> DatabaseOperationResponse:
    config = _merge_config(request, payload)
    try:
        engine = create_database_engine(config)
        already_exists = initialise_database(engine)
    except Exception as exc:  # pragma: no cover - FastAPI will capture details
        logger.exception("Failed to initialise database")
        return DatabaseOperationResponse(
            status="error",
            message="Failed to initialise database.",
            details=str(exc),
        )

    _store_runtime_config(request, config, engine=engine)
    return DatabaseOperationResponse(
        status="ok",
        message="Database tables already exist." if already_exists else "Database tables created.",
    )


@router.post("/settings/database/seed", response_model=SeedResponse)
def seed_database_endpoint(
    request: Request,
    payload: SeedRequest | None = None,
) -> SeedResponse:
    config = _merge_config(request, payload)
    excel_path = DEFAULT_EXCEL_PATH
    if payload and payload.excel_path:
        excel_input = Path(payload.excel_path).expanduser()
        if not excel_input.is_absolute():
            excel_input = PROJECT_ROOT / excel_input
        excel_path = excel_input.resolve()

    if not excel_path.exists():
        message = f"Excel file not found at {excel_path}"
        logger.error(message)
        return SeedResponse(status="error", message=message)

    rc, command, stdout, stderr = seed_database_from_excel(config, excel_path)
    if rc != 0:
        logger.error("Seed from Excel failed: %s", stderr or stdout)
        return SeedResponse(
            status="error",
            message="Seeding failed.",
            command=command,
            stdout=stdout,
            stderr=stderr,
        )

    _store_runtime_config(request, config)
    return SeedResponse(
        status="ok",
        message="Seed completed.",
        command=command,
        stdout=stdout,
        stderr=stderr,
    )


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/acronyms", response_model=list[AcronymResponse])
def list_acronyms(db: Session = Depends(get_db_session)) -> list[AcronymResponse]:
    records = app_api.list_acronyms(db)
    return [AcronymResponse(**record) for record in records]


@router.get("/sessions/{session_id}/dashboard", response_model=DashboardData)
def get_dashboard_data(
    session_id: int,
    db: Session = Depends(get_db_session),
) -> DashboardData:
    try:
        dimension_results = app_api.compute_dimension_averages(db, session_id=session_id)
        theme_results = app_api.compute_theme_averages(db, session_id=session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.user_message) from exc
    except ResilienceAssessmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.user_message) from exc

    theme_meta_rows = (
        db.query(
            ThemeORM.id.label("theme_id"),
            ThemeORM.name.label("theme_name"),
            ThemeORM.dimension_id.label("dimension_id"),
            DimensionORM.name.label("dimension_name"),
        )
        .join(DimensionORM, ThemeORM.dimension_id == DimensionORM.id)
        .all()
    )
    theme_meta = {
        row.theme_id: {
            "dimension_id": row.dimension_id,
            "dimension_name": row.dimension_name,
            "theme_name": row.theme_name,
        }
        for row in theme_meta_rows
    }

    dimension_scores = [
        AverageScore(
            id=result.id,
            name=result.name,
            average=_safe_average(result.average),
            coverage=result.coverage,
        )
        for result in dimension_results
    ]

    theme_scores: list[ThemeAverageScore] = []
    for result in theme_results:
        meta = theme_meta.get(result.id)
        if not meta:
            continue
        theme_scores.append(
            ThemeAverageScore(
                id=result.id,
                name=result.name,
                average=_safe_average(result.average),
                coverage=result.coverage,
                dimension_id=meta["dimension_id"],
                dimension_name=meta["dimension_name"],
            )
        )

    entries = (
        db.query(AssessmentEntryORM)
        .filter(AssessmentEntryORM.session_id == session_id)
        .all()
    )

    ratings_map: dict[int, tuple[float, str]] = {}
    for entry in entries:
        if entry.current_is_na:
            continue
        if entry.computed_score is not None:
            try:
                score_value = float(entry.computed_score)
            except (TypeError, ValueError):
                continue
            ratings_map[entry.topic_id] = (score_value, "computed")
            continue
        if entry.current_maturity is not None:
            ratings_map.setdefault(entry.topic_id, (float(entry.current_maturity), "rating"))

    topic_rows = (
        db.query(
            TopicORM.id.label("topic_id"),
            TopicORM.name.label("topic_name"),
            ThemeORM.id.label("theme_id"),
            ThemeORM.name.label("theme_name"),
            DimensionORM.id.label("dimension_id"),
            DimensionORM.name.label("dimension_name"),
        )
        .join(ThemeORM, TopicORM.theme_id == ThemeORM.id)
        .join(DimensionORM, ThemeORM.dimension_id == DimensionORM.id)
        .order_by(DimensionORM.name, ThemeORM.name, TopicORM.name)
        .all()
    )

    topic_scores: list[TopicScore] = []
    for row in topic_rows:
        rating = ratings_map.get(row.topic_id)
        if not rating:
            continue
        score_value, source = rating
        topic_scores.append(
            TopicScore(
                topic_id=row.topic_id,
                topic_name=row.topic_name,
                theme_id=row.theme_id,
                theme_name=row.theme_name,
                dimension_id=row.dimension_id,
                dimension_name=row.dimension_name,
                score=score_value,
                source=source,
            )
        )

    return DashboardData(
        dimensions=dimension_scores,
        themes=theme_scores,
        topic_scores=topic_scores,
    )


@router.get("/sessions/{session_id}/dashboard/figures", response_model=DashboardFiguresResponse)
def get_dashboard_figures(
    session_id: int,
    db: Session = Depends(get_db_session),
) -> DashboardFiguresResponse:
    try:
        payload = app_api.build_dashboard_figures(db, session_id=session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.user_message) from exc
    except ResilienceAssessmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.user_message) from exc

    return DashboardFiguresResponse(**payload)


@router.get("/dimensions", response_model=list[Dimension])
def list_dimensions(db: Session = Depends(get_db_session)) -> list[Dimension]:
    rows = (
        db.query(
            DimensionORM,
            func.count(func.distinct(ThemeORM.id)),
            func.count(func.distinct(TopicORM.id)),
        )
        .outerjoin(ThemeORM, ThemeORM.dimension_id == DimensionORM.id)
        .outerjoin(TopicORM, TopicORM.theme_id == ThemeORM.id)
        .group_by(DimensionORM.id)
        .order_by(DimensionORM.name)
        .all()
    )
    return [
        Dimension(
            id=dimension.id,
            name=dimension.name,
            description=dimension.description,
            image_filename=dimension.image_filename,
            image_alt=dimension.image_alt,
            theme_count=int(theme_count or 0),
            topic_count=int(topic_count or 0),
        )
        for dimension, theme_count, topic_count in rows
    ]


@router.get("/dimensions/{dimension_id}/themes", response_model=list[Theme])
def list_themes_for_dimension(
    dimension_id: int,
    db: Session = Depends(get_db_session),
) -> list[Theme]:
    dimension = db.get(DimensionORM, dimension_id)
    if dimension is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dimension not found")

    rows = (
        db.query(ThemeORM, func.count(TopicORM.id))
        .outerjoin(TopicORM, TopicORM.theme_id == ThemeORM.id)
        .filter(ThemeORM.dimension_id == dimension_id)
        .group_by(ThemeORM.id)
        .order_by(ThemeORM.name)
        .all()
    )
    return [
        Theme(
            id=theme.id,
            dimension_id=theme.dimension_id,
            name=theme.name,
            description=theme.description,
            category=theme.category,
            topic_count=int(topic_count or 0),
        )
        for theme, topic_count in rows
    ]


@router.get(
    "/dimensions/{dimension_id}/assessment",
    response_model=DimensionAssessmentResponse,
)
def get_dimension_assessment(
    dimension_id: int,
    session_id: int | None = None,
    db: Session = Depends(get_db_session),
) -> DimensionAssessmentResponse:
    dimension = db.get(DimensionORM, dimension_id)
    if dimension is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dimension not found")

    themes = (
        db.query(ThemeORM)
        .filter(ThemeORM.dimension_id == dimension_id)
        .order_by(ThemeORM.name)
        .all()
    )
    theme_ids = [theme.id for theme in themes]

    topics: list[TopicORM] = []
    if theme_ids:
        topics = (
            db.query(TopicORM)
            .filter(TopicORM.theme_id.in_(theme_ids))
            .order_by(TopicORM.name)
            .all()
        )

    topic_ids = [topic.id for topic in topics]

    entries_map: dict[int, AssessmentEntryORM] = {}
    if session_id and topic_ids:
        entries = (
            db.query(AssessmentEntryORM)
            .filter(
                AssessmentEntryORM.session_id == session_id,
                AssessmentEntryORM.topic_id.in_(topic_ids),
            )
            .all()
        )
        entries_map = {entry.topic_id: entry for entry in entries}

    guidance_map: dict[int, dict[int, list[str]]] = {}
    if topic_ids:
        explanations = (
            db.query(ExplanationORM)
            .filter(ExplanationORM.topic_id.in_(topic_ids))
            .order_by(ExplanationORM.topic_id, ExplanationORM.level, ExplanationORM.id)
            .all()
        )
        for explanation in explanations:
            guidance_map.setdefault(explanation.topic_id, {}).setdefault(explanation.level, []).append(
                explanation.text
            )

    theme_guidance_map: dict[int, list[ThemeLevelGuidance]] = {theme.id: [] for theme in themes}
    if theme_ids:
        theme_guidance_rows = (
            db.query(ThemeLevelGuidanceORM)
            .filter(ThemeLevelGuidanceORM.theme_id.in_(theme_ids))
            .order_by(ThemeLevelGuidanceORM.theme_id, ThemeLevelGuidanceORM.level)
            .all()
        )
        for row in theme_guidance_rows:
            theme_guidance_map.setdefault(row.theme_id, []).append(
                ThemeLevelGuidance(level=row.level, description=row.description)
            )

    rating_scale = [
        RatingScale(level=scale.level, label=scale.label, description=scale.description)
        for scale in db.query(RatingScaleORM).order_by(RatingScaleORM.level)
    ]

    topics_by_theme: dict[int, list[TopicORM]] = {theme.id: [] for theme in themes}
    for topic in topics:
        topics_by_theme.setdefault(topic.theme_id, []).append(topic)

    allowed_states = {"not_started", "in_progress", "complete"}
    progress_totals = {state: 0 for state in allowed_states}

    def _parse_evidence(entry: AssessmentEntryORM | None) -> list[str]:
        if entry is None or not entry.evidence_links:
            return []
        try:
            parsed = json.loads(entry.evidence_links)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
            if parsed is not None:
                value = str(parsed).strip()
                return [value] if value else []
        except json.JSONDecodeError:
            value = entry.evidence_links.strip()
            return [value] if value else []
        return []

    theme_blocks: list[ThemeAssessmentBlock] = []
    for theme in themes:
        theme_topics: list[TopicAssessmentDetail] = []
        for topic in topics_by_theme.get(theme.id, []):
            entry = entries_map.get(topic.id)
            evidence = _parse_evidence(entry)

            if entry:
                state = entry.progress_state if entry.progress_state in allowed_states else None
                if state is None:
                    if entry.current_is_na or entry.current_maturity is not None:
                        if entry.desired_is_na or entry.desired_maturity is not None:
                            state = "complete"
                        else:
                            state = "in_progress"
                    else:
                        state = "not_started"
            else:
                state = "not_started"

            progress_totals[state] = progress_totals.get(state, 0) + 1

            theme_topics.append(
                TopicAssessmentDetail(
                    id=topic.id,
                    name=topic.name,
                    description=topic.description,
                    impact=topic.impact,
                    benefits=topic.benefits,
                    basic=topic.basic,
                    advanced=topic.advanced,
                    evidence=topic.evidence,
                    regulations=topic.regulations,
                    current_maturity=(
                        entry.current_maturity if entry and not entry.current_is_na else None
                    ),
                    current_is_na=bool(entry.current_is_na) if entry else False,
                    desired_maturity=(
                        entry.desired_maturity if entry and not entry.desired_is_na else None
                    ),
                    desired_is_na=bool(entry.desired_is_na) if entry else False,
                    comment=entry.comment if entry else None,
                    evidence_links=evidence,
                    progress_state=state,
                    guidance=guidance_map.get(topic.id, {}),
                    theme_id=theme.id,
                    theme_name=theme.name,
                )
            )

        theme_blocks.append(
            ThemeAssessmentBlock(
                id=theme.id,
                name=theme.name,
                description=theme.description,
                category=theme.category,
                topic_count=len(theme_topics),
                topics=theme_topics,
                generic_guidance=theme_guidance_map.get(theme.id, []),
            )
        )

    total_topics = len(topics)
    completed_topics = progress_totals.get("complete", 0)
    in_progress_topics = progress_totals.get("in_progress", 0)
    not_started_topics = progress_totals.get("not_started", 0)
    completion_percent = (
        round((completed_topics / total_topics) * 100, 1) if total_topics > 0 else 0.0
    )

    dimension_payload = Dimension(
        id=dimension.id,
        name=dimension.name,
        description=dimension.description,
        image_filename=dimension.image_filename,
        image_alt=dimension.image_alt,
        theme_count=len(themes),
        topic_count=total_topics,
    )

    progress = ProgressSummary(
        total_topics=total_topics,
        completed_topics=completed_topics,
        in_progress_topics=in_progress_topics,
        not_started_topics=not_started_topics,
        completion_percent=completion_percent,
    )

    return DimensionAssessmentResponse(
        dimension=dimension_payload,
        rating_scale=rating_scale,
        themes=theme_blocks,
        progress=progress,
    )


@router.get("/themes/{theme_id}/topics", response_model=ThemeTopicsResponse)
def get_theme_topics(
    theme_id: int,
    session_id: int | None = None,
    db: Session = Depends(get_db_session),
) -> ThemeTopicsResponse:
    theme = db.get(ThemeORM, theme_id)
    if theme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theme not found")

    topics = (
        db.query(TopicORM)
        .filter(TopicORM.theme_id == theme_id)
        .order_by(TopicORM.name)
        .all()
    )
    topic_ids = [topic.id for topic in topics]

    ratings_map: dict[int, AssessmentEntryORM] = {}
    if session_id and topic_ids:
        entries = (
            db.query(AssessmentEntryORM)
            .filter(
                AssessmentEntryORM.session_id == session_id,
                AssessmentEntryORM.topic_id.in_(topic_ids),
            )
            .all()
        )
        ratings_map = {entry.topic_id: entry for entry in entries}

    guidance_map: dict[int, dict[int, list[str]]] = {}
    if topic_ids:
        explanations = (
            db.query(ExplanationORM)
            .filter(ExplanationORM.topic_id.in_(topic_ids))
            .order_by(ExplanationORM.topic_id, ExplanationORM.level, ExplanationORM.id)
            .all()
        )
        for explanation in explanations:
            guidance_map.setdefault(explanation.topic_id, {}).setdefault(explanation.level, []).append(
                explanation.text
            )

    rating_scale = [
        RatingScale(level=scale.level, label=scale.label, description=scale.description)
        for scale in db.query(RatingScaleORM).order_by(RatingScaleORM.level)
    ]

    generic_guidance = [
        ThemeLevelGuidance(level=gl.level, description=gl.description)
        for gl in (
            db.query(ThemeLevelGuidanceORM)
            .filter(ThemeLevelGuidanceORM.theme_id == theme_id)
            .order_by(ThemeLevelGuidanceORM.level)
            .all()
        )
    ]

    topic_details = []
    for topic in topics:
        entry = ratings_map.get(topic.id)
        evidence_links: list[str] = []
        if entry and entry.evidence_links:
            try:
                parsed = json.loads(entry.evidence_links)
                if isinstance(parsed, list):
                    evidence_links = [str(item).strip() for item in parsed if str(item).strip()]
                elif parsed is not None:
                    evidence_links = [str(parsed).strip()]
            except json.JSONDecodeError:
                evidence_links = [entry.evidence_links]
        topic_details.append(
            TopicDetail(
                id=topic.id,
                name=topic.name,
                description=topic.description,
                impact=topic.impact,
                benefits=topic.benefits,
                basic=topic.basic,
                advanced=topic.advanced,
                evidence=topic.evidence,
                regulations=topic.regulations,
                current_maturity=(
                    entry.current_maturity if entry and not entry.current_is_na else None
                ),
                current_is_na=bool(entry.current_is_na) if entry else False,
                desired_maturity=(
                    entry.desired_maturity if entry and not entry.desired_is_na else None
                ),
                desired_is_na=bool(entry.desired_is_na) if entry else False,
                comment=entry.comment if entry else None,
                evidence_links=evidence_links,
                progress_state=entry.progress_state if entry else "not_started",
                guidance=guidance_map.get(topic.id, {}),
            )
        )

    theme_schema = Theme(
        id=theme.id,
        dimension_id=theme.dimension_id,
        name=theme.name,
        description=theme.description,
        category=theme.category,
        topic_count=len(topic_details),
    )

    return ThemeTopicsResponse(
        theme=theme_schema,
        topics=topic_details,
        rating_scale=rating_scale,
        generic_guidance=generic_guidance,
    )


@router.get("/sessions", response_model=list[SessionListItem])
def list_sessions(db: Session = Depends(get_db_session)) -> list[SessionListItem]:
    repo = SessionRepo(db)
    sessions = repo.list_all()
    return [
        SessionListItem(
            id=item.id,
            name=item.name,
            assessor=item.assessor,
            created_at=item.created_at,
        )
        for item in sessions
    ]


@router.post("/sessions", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db_session),
) -> SessionSummary:
    try:
        session_obj = app_api.create_assessment_session(
            db,
            name=payload.name,
            assessor=payload.assessor,
            notes=payload.notes,
            created_at=payload.created_at,
        )
        db.commit()
        db.refresh(session_obj)
    except Exception:
        db.rollback()
        raise

    return SessionSummary(
        id=session_obj.id,
        name=session_obj.name,
        assessor=session_obj.assessor,
        notes=session_obj.notes,
        created_at=session_obj.created_at,
    )


@router.post("/sessions/combine", response_model=SessionSummary)
def combine_sessions(
    payload: SessionCombineRequest,
    db: Session = Depends(get_db_session),
) -> SessionSummary:
    if not payload.source_session_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No source sessions provided")

    try:
        master = app_api.combine_sessions_to_master(
            db,
            source_session_ids=payload.source_session_ids,
            name=payload.name,
        )
        db.commit()
        db.refresh(master)
    except Exception:
        db.rollback()
        raise

    return SessionSummary(
        id=master.id,
        name=master.name,
        assessor=master.assessor,
        notes=master.notes,
        created_at=master.created_at,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: int, db: Session = Depends(get_db_session)) -> SessionDetail:
    summary_data = app_api.get_session_summary(db, session_id=session_id)
    summary = SessionSummary(
        id=summary_data["id"],
        name=summary_data["name"],
        assessor=summary_data.get("assessor"),
        notes=summary_data.get("notes"),
        created_at=summary_data["created_at"],
    )
    stats_data = summary_data.get("statistics", {})
    statistics = SessionStatistics(
        total_topics=stats_data.get("total_topics", 0),
        total_entries=stats_data.get("total_entries", 0),
        rated_entries=stats_data.get("rated_entries", 0),
        na_entries=stats_data.get("na_entries", 0),
        computed_entries=stats_data.get("computed_entries", 0),
        completion_percent=stats_data.get("completion_percent", 0.0),
        rating_percent=stats_data.get("rating_percent", 0.0),
    )
    return SessionDetail(summary=summary, statistics=statistics)


@router.post("/sessions/{session_id}/ratings", status_code=status.HTTP_204_NO_CONTENT)
def update_ratings(
    session_id: int,
    payload: RatingBulkUpdateRequest,
    db: Session = Depends(get_db_session),
) -> None:
    if payload.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID mismatch")

    try:
        for update in payload.updates:
            current_is_na = update.current_is_na
            desired_is_na = update.desired_is_na or current_is_na
            desired_maturity = update.desired_maturity
            if current_is_na:
                desired_is_na = True
                desired_maturity = None
            elif desired_is_na:
                desired_maturity = None
            elif desired_maturity is None:
                desired_maturity = update.current_maturity

            app_api.record_topic_rating(
                db,
                session_id=session_id,
                topic_id=update.topic_id,
                current_maturity=update.current_maturity,
                desired_maturity=desired_maturity,
                current_is_na=current_is_na,
                desired_is_na=desired_is_na,
                comment=update.comment,
                evidence_links=update.evidence_links,
                progress_state=update.progress_state or "in_progress",
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.post("/sessions/{session_id}/ratings/single", status_code=status.HTTP_204_NO_CONTENT)
def update_single_rating(
    session_id: int,
    payload: RatingUpdate,
    db: Session = Depends(get_db_session),
) -> None:
    try:
        current_is_na = payload.current_is_na
        desired_is_na = payload.desired_is_na or current_is_na
        desired_maturity = payload.desired_maturity
        if current_is_na:
            desired_is_na = True
            desired_maturity = None
        elif desired_is_na:
            desired_maturity = None
        elif desired_maturity is None:
            desired_maturity = payload.current_maturity

        app_api.record_topic_rating(
            db,
            session_id=session_id,
            topic_id=payload.topic_id,
            current_maturity=payload.current_maturity,
            desired_maturity=desired_maturity,
            current_is_na=current_is_na,
            desired_is_na=desired_is_na,
            comment=payload.comment,
            evidence_links=payload.evidence_links,
            progress_state=payload.progress_state or "in_progress",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.get("/sessions/{session_id}/exports/json")
def export_session_json(session_id: int, db: Session = Depends(get_db_session)) -> JSONResponse:
    topics_df, entries_df = app_api.export_session_results(db, session_id=session_id)
    payload_str = make_json_export_payload(session_id, topics_df, entries_df)
    payload = json.loads(payload_str)
    return JSONResponse(content=payload)


@router.get("/sessions/{session_id}/exports/xlsx")
def export_session_xlsx(session_id: int, db: Session = Depends(get_db_session)) -> StreamingResponse:
    topics_df, entries_df = app_api.export_session_results(db, session_id=session_id)
    xlsx_bytes = make_xlsx_export_bytes(topics_df, entries_df)
    filename = f"assessment_{session_id}.xlsx"
    stream = io.BytesIO(xlsx_bytes)
    stream.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )

@router.post("/sessions/{session_id}/imports/xlsx", response_model=ImportResponse)
async def import_session_xlsx(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> ImportResponse:
    allowed_types = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }

    if file.content_type not in allowed_types:
        return ImportResponse(
            status="error",
            message="Unsupported file type. Please upload an Excel .xlsx file.",
        )

    file_bytes = await file.read()

    try:
        dataframe = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0)
    except Exception as exc:  # pragma: no cover - pandas error detail varies
        return ImportResponse(
            status="error",
            message="Unable to read Excel file. Please verify the template.",
            details=str(exc),
        )

    try:
        processed = app_api.import_session_results(db, session_id=session_id, dataframe=dataframe)
        db.commit()
        return ImportResponse(
            status="ok",
            message=f"Imported {processed} entries.",
            processed=processed,
        )
    except MultipleValidationError as exc:
        db.rollback()
        error_details = [
            {
                "field": err.field,
                "message": err.message,
                "value": err.value,
                "details": {
                    k: (str(v) if not isinstance(v, (int, float, bool)) else v)
                    for k, v in (getattr(err, "details", {}) or {}).items()
                },
            }
            for err in exc.validation_errors
        ]
        return ImportResponse(
            status="error",
            message="Import failed due to validation errors.",
            processed=0,
            errors=error_details,
            details=json.dumps(exc.details, default=str),
        )
    except ResilienceAssessmentError as exc:
        db.rollback()
        return ImportResponse(
            status="error",
            message=exc.user_message,
            processed=0,
            details=json.dumps(exc.details, default=str),
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        db.rollback()
        logger.exception("Unexpected error importing assessment", exc_info=exc)
        return ImportResponse(
            status="error",
            message="Unexpected error during import.",
            processed=0,
            details=str(exc),
        )
