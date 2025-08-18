from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Iterable
import math
from sqlalchemy.orm import Session
from ..infrastructure.models import (
    DimensionORM, ThemeORM, TopicORM, AssessmentEntryORM, RatingScaleORM
)

def clamp_rating(level: Optional[int]) -> Optional[int]:
    if level is None:
        return None
    if not (1 <= level <= 5):
        raise ValueError("Rating must be between 1 and 5 inclusive.")
    return int(level)

@dataclass(frozen=True)
class AverageResult:
    id: int
    name: str
    average: float
    coverage: float  # 0..1

class ScoringService:
    def __init__(self, s: Session):
        self.s = s

    def compute_theme_averages(self, session_id: int) -> list[AverageResult]:
        # average per Theme: mean of rated Topic entries in that Theme
        q = (
            self.s.query(ThemeORM.id, ThemeORM.name)
            .join(TopicORM, TopicORM.theme_id == ThemeORM.id)
            .filter(TopicORM.id.isnot(None))
            .distinct()
        ).all()

        results: list[AverageResult] = []
        for theme_id, theme_name in q:
            topics = self.s.query(TopicORM.id).filter(TopicORM.theme_id == theme_id).all()
            topic_ids = [t[0] for t in topics]
            total = len(topic_ids)
            if total == 0:
                results.append(AverageResult(theme_id, theme_name, float("nan"), 0.0))
                continue
            entries = self.s.query(AssessmentEntryORM).filter(
                AssessmentEntryORM.session_id == session_id,
                AssessmentEntryORM.topic_id.in_(topic_ids),
                AssessmentEntryORM.is_na == False,
            ).all()
            rated_vals = []
            for e in entries:
                val = e.computed_score if e.computed_score is not None else e.rating_level
                if val is not None:
                    rated_vals.append(float(val))
            coverage = len(rated_vals) / total if total else 0.0
            avg = sum(rated_vals) / len(rated_vals) if rated_vals else float("nan")
            results.append(AverageResult(theme_id, theme_name, avg, coverage))
        return results

    def compute_dimension_averages(self, session_id: int) -> list[AverageResult]:
        # average per Dimension: mean of theme averages (exclude NaN)
        dims = self.s.query(DimensionORM.id, DimensionORM.name).order_by(DimensionORM.name).all()
        theme_results = self.compute_theme_averages(session_id)
        # group by dimension using ORM relationships
        theme_by_dim: dict[int, list[AverageResult]] = {d[0]: [] for d in dims}
        for theme in self.s.query(ThemeORM.id, ThemeORM.dimension_id).all():
            trec = next((t for t in theme_results if t.id == theme.id), None)
            if trec:
                theme_by_dim[theme.dimension_id].append(trec)

        results: list[AverageResult] = []
        for dim_id, dim_name in dims:
            ts = theme_by_dim.get(dim_id, [])
            vals = [t.average for t in ts if not math.isnan(t.average)]
            coverage = sum(t.coverage for t in ts) / len(ts) if ts else 0.0
            avg = sum(vals) / len(vals) if vals else float("nan")
            results.append(AverageResult(dim_id, dim_name, avg, coverage))
        return results
