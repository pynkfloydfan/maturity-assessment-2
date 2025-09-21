from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Dimension:
    id: int
    name: str
    created_at: datetime


@dataclass(slots=True)
class Theme:
    id: int
    dimension_id: int
    name: str
    created_at: datetime


@dataclass(slots=True)
class Topic:
    id: int
    theme_id: int
    name: str
    created_at: datetime


@dataclass(slots=True)
class RatingScale:
    level: int  # 1..5
    label: str  # e.g. "Initial", "Managed", ...


@dataclass(slots=True)
class Explanation:
    id: int
    topic_id: int
    level: int
    text: str


@dataclass(slots=True)
class AssessmentSession:
    id: int
    name: str
    assessor: str | None
    organization: str | None
    created_at: datetime
    notes: str | None = None


@dataclass(slots=True)
class AssessmentEntry:
    id: int
    session_id: int
    topic_id: int
    rating_level: int | None  # None if N/A
    is_na: bool
    comment: str | None
    created_at: datetime
