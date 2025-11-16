from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from sqlalchemy import case, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# If your project defines custom exceptions/handlers and you want them here,
# uncomment and adjust the imports:
from ..infrastructure.models import (
    AssessmentEntryORM,
    DimensionORM,
    ThemeORM,
    TopicORM,
)


def clamp_rating(level: int | None) -> int | None:
    if level is None:
        return None
    if not (1 <= level <= 5):
        raise ValueError("Rating must be between 1 and 5 inclusive.")
    return int(level)


@dataclass
class AverageResult:
    id: int
    name: str
    average: float  # float('nan') if no rated data
    coverage: float  # 0..1 proportion


class ScoringService:
    def __init__(self, s: Session, logger: logging.Logger | None = None):
        self.s = s
        self.logger = logger or logging.getLogger(__name__)

    def compute_theme_averages(self, session_id: int) -> list[AverageResult]:
        """
        Per-theme average for a session via a single aggregated query.
        - Average uses COALESCE(computed_score, current_maturity).
        - Excludes entries with current_is_na=True.
        - coverage = rated_topics / total_topics in theme.
        - Includes themes with zero topics (avg=NaN, coverage=0.0).
        """
        try:
            # Total topics per theme (subquery)
            total_topics_sq = (
                self.s.query(
                    TopicORM.theme_id.label("theme_id"),
                    func.count(TopicORM.id).label("total_topics"),
                )
                .group_by(TopicORM.theme_id)
                .subquery()
            )

            # Score expression: prefer computed_score, fallback to current maturity
            score_expr = func.coalesce(
                AssessmentEntryORM.computed_score,
                AssessmentEntryORM.current_maturity,
            )

            # Count only rated entries that are not N/A and have a score
            rated_count_expr = func.coalesce(
                func.sum(
                    case(
                        ((AssessmentEntryORM.current_is_na.is_(False)) & (score_expr.isnot(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("rated_count")

            # Average only over non-N/A scores; else NULL which we translate to NaN
            avg_expr = func.avg(
                case(
                    ((AssessmentEntryORM.current_is_na.is_(False)), score_expr),
                    else_=None,
                )
            ).label("avg_score")

            # Aggregate per theme, preserving themes with no topics/entries
            q = (
                self.s.query(
                    ThemeORM.id.label("theme_id"),
                    ThemeORM.name.label("theme_name"),
                    ThemeORM.dimension_id.label("dimension_id"),
                    func.coalesce(total_topics_sq.c.total_topics, 0).label("total_topics"),
                    rated_count_expr,
                    avg_expr,
                )
                .outerjoin(total_topics_sq, total_topics_sq.c.theme_id == ThemeORM.id)
                .outerjoin(TopicORM, TopicORM.theme_id == ThemeORM.id)
                .outerjoin(
                    AssessmentEntryORM,
                    (AssessmentEntryORM.topic_id == TopicORM.id)
                    & (AssessmentEntryORM.session_id == session_id),
                )
                .group_by(
                    ThemeORM.id,
                    ThemeORM.name,
                    ThemeORM.dimension_id,
                    total_topics_sq.c.total_topics,
                )
                .order_by(ThemeORM.name)
            )

            rows = q.all()
            results: list[AverageResult] = []

            for theme_id, theme_name, _dimension_id, total_topics, rated_count, avg_score in rows:
                total_topics = int(total_topics or 0)
                rated_count = int(rated_count or 0)
                coverage = (rated_count / total_topics) if total_topics else 0.0
                avg = float(avg_score) if avg_score is not None else float("nan")
                results.append(AverageResult(theme_id, theme_name, avg, coverage))

            self.logger.debug(
                "Computed theme aggregates for session %s: %d themes", session_id, len(results)
            )
            return results

        except SQLAlchemyError:
            self.logger.exception(
                "Database error computing theme averages for session %s", session_id
            )
            raise
        except Exception:
            self.logger.exception(
                "Unexpected error computing theme averages for session %s", session_id
            )
            raise

    def compute_dimension_averages(self, session_id: int) -> list[AverageResult]:
        """
        Per-dimension average/coverage from per-theme aggregates.
        - Dimension average = mean(theme.average) excluding NaNs.
        - Dimension coverage = mean(theme.coverage) (equal-weighted across themes).
        - If a dimension has no themes: avg=NaN, coverage=0.0
        """

        try:
            # Get per-theme aggregates once
            theme_results = self.compute_theme_averages(session_id)

            # Map theme -> dimension id from the DB (small query)
            theme_dim_pairs = self.s.query(ThemeORM.id, ThemeORM.dimension_id).all()
            theme_to_dim = {tid: did for (tid, did) in theme_dim_pairs}

            # Fetch dimension names (for display)
            dims = (
                self.s.query(DimensionORM.id, DimensionORM.name).order_by(DimensionORM.name).all()
            )

            # Group themes by dimension
            themes_by_dim: dict[int, list[AverageResult]] = {d_id: [] for (d_id, _name) in dims}
            for tr in theme_results:
                dim_id = theme_to_dim.get(tr.id)
                if dim_id is not None:
                    themes_by_dim.setdefault(dim_id, []).append(tr)

            results: list[AverageResult] = []
            for dim_id, dim_name in dims:
                ts = themes_by_dim.get(dim_id, [])
                if not ts:
                    results.append(AverageResult(dim_id, dim_name, float("nan"), 0.0))
                    continue

                # Exclude NaN averages when computing the mean
                theme_avgs = [t.average for t in ts if not math.isnan(t.average)]
                avg = (sum(theme_avgs) / len(theme_avgs)) if theme_avgs else float("nan")

                # Coverage is the simple mean of theme coverages (equal-weighted)
                coverage = sum(t.coverage for t in ts) / len(ts)

                results.append(AverageResult(dim_id, dim_name, avg, coverage))

            self.logger.info(
                "Computed dimension averages for session %s: %d dimensions",
                session_id,
                len(results),
            )
            return results

        except SQLAlchemyError:
            self.logger.exception(
                "Database error computing dimension averages for session %s", session_id
            )
            raise
        except Exception:
            self.logger.exception(
                "Unexpected error computing dimension averages for session %s", session_id
            )
            raise
