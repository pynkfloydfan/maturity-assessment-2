from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Dimension(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    image_filename: Optional[str] = None
    image_alt: Optional[str] = None
    theme_count: Optional[int] = None
    topic_count: Optional[int] = None


class Theme(BaseModel):
    id: int
    dimension_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    topic_count: Optional[int] = None


class Topic(BaseModel):
    id: int
    theme_id: int
    name: str
    description: Optional[str] = None


class ThemeLevelGuidance(BaseModel):
    level: int
    description: str


class RatingScale(BaseModel):
    level: int
    label: str
    description: Optional[str] = None


class TopicRating(BaseModel):
    topic_id: int
    rating_level: Optional[int] = Field(default=None, ge=1, le=5)
    is_na: bool = False
    comment: Optional[str] = None
    updated_at: Optional[datetime] = None


class TopicGuidance(BaseModel):
    level: int
    bullets: list[str]


class TopicDetail(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    rating_level: Optional[int] = None
    is_na: bool = False
    comment: Optional[str] = None
    guidance: dict[int, list[str]] = Field(default_factory=dict)


class ThemeTopicsResponse(BaseModel):
    theme: Theme
    topics: list[TopicDetail]
    rating_scale: list[RatingScale]
    generic_guidance: list[ThemeLevelGuidance]


class AverageScore(BaseModel):
    id: int
    name: str
    average: Optional[float] = None
    coverage: Optional[float] = None


class ThemeAverageScore(AverageScore):
    dimension_id: int
    dimension_name: str


class TopicScore(BaseModel):
    topic_id: int
    topic_name: str
    theme_id: int
    theme_name: str
    dimension_id: int
    dimension_name: str
    score: float
    source: Optional[Literal["rating", "computed"]] = None


class DashboardData(BaseModel):
    dimensions: list[AverageScore]
    themes: list[ThemeAverageScore]
    topic_scores: list[TopicScore]


class DashboardTile(BaseModel):
    id: int
    name: str
    average: Optional[float] = None
    coverage: Optional[float] = None
    color: Optional[str] = None


class PlotlyFigure(BaseModel):
    data: list[Any]
    layout: dict[str, Any]
    frames: Optional[list[Any]] = None

    class Config:
        extra = "allow"


class DashboardFiguresResponse(BaseModel):
    tiles: list[DashboardTile]
    radar: Optional[PlotlyFigure] = None


class SessionSummary(BaseModel):
    id: int
    name: str
    assessor: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class SessionStatistics(BaseModel):
    total_topics: int
    total_entries: int
    rated_entries: int
    na_entries: int
    computed_entries: int
    completion_percent: float
    rating_percent: float


class SessionDetail(BaseModel):
    summary: SessionSummary
    statistics: SessionStatistics


class SessionListItem(BaseModel):
    id: int
    name: str
    assessor: Optional[str] = None
    created_at: datetime


class SessionCreateRequest(BaseModel):
    name: str
    assessor: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class SessionCombineRequest(BaseModel):
    source_session_ids: list[int]
    name: str


class RatingUpdate(BaseModel):
    topic_id: int
    rating_level: Optional[int] = Field(default=None, ge=1, le=5)
    is_na: bool = False
    comment: Optional[str] = None


class RatingBulkUpdateRequest(BaseModel):
    session_id: int
    updates: list[RatingUpdate]


class DatabaseInitRequest(BaseModel):
    backend: Literal["sqlite", "mysql"] | None = None
    sqlite_path: Optional[str] = None
    mysql_host: Optional[str] = None
    mysql_port: Optional[int] = None
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_database: Optional[str] = None


class SeedRequest(DatabaseInitRequest):
    excel_path: Optional[str] = None


class ExportResponse(BaseModel):
    json_url: str
    xlsx_url: str


class DatabaseSettings(BaseModel):
    backend: Literal["sqlite", "mysql"]
    sqlite_path: Optional[str] = None
    mysql_host: Optional[str] = None
    mysql_port: Optional[int] = None
    mysql_user: Optional[str] = None
    mysql_database: Optional[str] = None


class DatabaseOperationResponse(BaseModel):
    status: Literal["ok", "error"]
    message: str
    details: Optional[str] = None


class SeedResponse(DatabaseOperationResponse):
    command: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class AcronymResponse(BaseModel):
    id: int
    acronym: str
    full_term: str
    meaning: Optional[str] = None


class ImportResponse(DatabaseOperationResponse):
    processed: int = 0
    errors: Optional[list[dict[str, object]]] = None

