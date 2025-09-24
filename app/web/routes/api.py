from __future__ import annotations

import io
import json
import logging
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.application import api as app_api
from app.infrastructure.config import DatabaseConfig
from app.infrastructure.db import create_database_engine, create_session_factory
from app.infrastructure.exceptions import ResilienceAssessmentError, SessionNotFoundError
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
    AverageScore,
    DashboardData,
    DashboardFiguresResponse,
    DatabaseInitRequest,
    DatabaseOperationResponse,
    DatabaseSettings,
    Dimension,
    RatingBulkUpdateRequest,
    RatingScale,
    RatingUpdate,
    SeedRequest,
    SeedResponse,
    SessionCombineRequest,
    SessionCreateRequest,
    SessionDetail,
    SessionListItem,
    SessionSummary,
    SessionStatistics,
    Theme,
    ThemeLevelGuidance,
    ThemeAverageScore,
    ThemeTopicsResponse,
    TopicDetail,
    TopicScore,
)

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = APP_DIR.parent
DEFAULT_EXCEL_PATH = (APP_DIR / "source_data" / "enhanced_operational_resilience_maturity_v6.xlsx").resolve()


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
        initialise_database(engine)
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
        message="Database tables created or already exist.",
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
        if entry.is_na:
            continue
        if entry.computed_score is not None:
            try:
                score_value = float(entry.computed_score)
            except (TypeError, ValueError):
                continue
            ratings_map[entry.topic_id] = (score_value, "computed")
            continue
        if entry.rating_level is not None:
            ratings_map.setdefault(entry.topic_id, (float(entry.rating_level), "rating"))

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
        db.query(DimensionORM, func.count(ThemeORM.id))
        .outerjoin(ThemeORM, ThemeORM.dimension_id == DimensionORM.id)
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
        )
        for dimension, theme_count in rows
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
        topic_details.append(
            TopicDetail(
                id=topic.id,
                name=topic.name,
                description=topic.description,
                rating_level=(entry.rating_level if entry and not entry.is_na else None),
                is_na=bool(entry.is_na) if entry else False,
                comment=entry.comment if entry else None,
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
            organization=item.organization,
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
            organization=payload.organization,
            notes=payload.notes,
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
        organization=session_obj.organization,
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
        organization=master.organization,
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
        organization=summary_data.get("organization"),
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
            rating_level = update.rating_level if not update.is_na else None
            app_api.record_topic_rating(
                db,
                session_id=session_id,
                topic_id=update.topic_id,
                rating_level=rating_level,
                is_na=update.is_na,
                comment=update.comment,
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
        rating_level = payload.rating_level if not payload.is_na else None
        app_api.record_topic_rating(
            db,
            session_id=session_id,
            topic_id=payload.topic_id,
            rating_level=rating_level,
            is_na=payload.is_na,
            comment=payload.comment,
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

