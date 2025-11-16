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
    created_at: datetime
    notes: str | None = None


@dataclass(slots=True)
class AssessmentEntry:
    id: int
    session_id: int
    topic_id: int
    current_maturity: int | None
    current_is_na: bool
    desired_maturity: int | None
    desired_is_na: bool
    comment: str | None
    evidence_links: list[str] | None
    progress_state: str
    computed_score: float | None = None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class Acronym:
    id: int
    acronym: str
    full_term: str
    meaning: str | None
    created_at: datetime
