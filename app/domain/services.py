from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Iterable, List
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

@dataclass
class AverageResult:
    id: int
    name: str
    average: float   # float('nan') if no rated data
    coverage: float  # 0..1 proportion

class ScoringService:
    def __init__(self, s: Session):
        self.s = s

    def compute_theme_averages(self, session_id: int) -> List[AverageResult]:
        """Per-theme average for a session.
        - Average uses COALESCE(computed_score, rating_level).
        - Excludes entries with is_na=True.
        - coverage = rated_topics / total_topics in theme.
        """
        themes = self.s.query(ThemeORM.id, ThemeORM.name).order_by(ThemeORM.name).all()
        results: List[AverageResult] = []

        for theme_id, theme_name in themes:
            # Total topics under this theme
            total_topics = (
                self.s.query(TopicORM.id)
                .filter(TopicORM.theme_id == theme_id)
                .count()
            )

            if total_topics == 0:
                results.append(AverageResult(theme_id, theme_name, float("nan"), 0.0))
                continue

            # Pull entries for this session+theme, excluding N/A
            entries = (
                self.s.query(AssessmentEntryORM)
                .join(TopicORM, TopicORM.id == AssessmentEntryORM.topic_id)
                .filter(
                    AssessmentEntryORM.session_id == session_id,
                    TopicORM.theme_id == theme_id,
                    AssessmentEntryORM.is_na == False,
                )
                .all()
            )

            rated_vals = []
            for e in entries:
                # Fallback to rating_level if computed_score is None
                v = e.computed_score if e.computed_score is not None else e.rating_level
                if v is not None:
                    rated_vals.append(float(v))

            coverage = len(rated_vals) / total_topics if total_topics else 0.0
            avg = sum(rated_vals) / len(rated_vals) if rated_vals else float("nan")
            results.append(AverageResult(theme_id, theme_name, avg, coverage))

        return results

    def compute_dimension_averages(self, session_id: int) -> List[AverageResult]:
        """Per-dimension average = mean of theme averages (excluding NaNs).
        coverage = mean(theme.coverage) across themes in the dimension.
        """
        dims = self.s.query(DimensionORM.id, DimensionORM.name).order_by(DimensionORM.name).all()
        theme_results = self.compute_theme_averages(session_id)

        # Build mapping: dimension_id -> [theme AverageResult]
        theme_dim_pairs = self.s.query(ThemeORM.id, ThemeORM.dimension_id).all()
        themes_by_dim: dict[int, list[AverageResult]] = {d_id: [] for (d_id, _) in dims}
        for theme_id, dim_id in theme_dim_pairs:
            tr = next((t for t in theme_results if t.id == theme_id), None)
            if tr:
                themes_by_dim[dim_id].append(tr)

        results: List[AverageResult] = []
        for dim_id, dim_name in dims:
            ts = themes_by_dim.get(dim_id, [])
            if not ts:
                results.append(AverageResult(dim_id, dim_name, float("nan"), 0.0))
                continue

            # Exclude NaN theme averages when computing the dimension mean
            theme_avgs = [t.average for t in ts if not math.isnan(t.average)]
            avg = sum(theme_avgs) / len(theme_avgs) if theme_avgs else float("nan")

            # Coverage is the mean of theme coverages (simple, equal-weighted)
            coverage = sum(t.coverage for t in ts) / len(ts)

            results.append(AverageResult(dim_id, dim_name, avg, coverage))

        return results
