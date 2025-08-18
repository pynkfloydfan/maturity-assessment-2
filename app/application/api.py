from __future__ import annotations
from typing import Optional
import pandas as pd
from sqlalchemy.orm import Session
from ..infrastructure.repositories import DimensionRepo, ThemeRepo, TopicRepo, SessionRepo, EntryRepo, RatingScaleRepo
from ..infrastructure.models import DimensionORM, ThemeORM, TopicORM, AssessmentEntryORM
from ..domain.services import ScoringService

def list_dimensions_with_topics(s: Session) -> pd.DataFrame:
    rows = (
        s.query(DimensionORM.name.label("Dimension"),
                ThemeORM.name.label("Theme"),
                TopicORM.id.label("TopicID"),
                TopicORM.name.label("Topic"))
        .join(ThemeORM, ThemeORM.dimension_id == DimensionORM.id)
        .join(TopicORM, TopicORM.theme_id == ThemeORM.id)
        .order_by(DimensionORM.name, ThemeORM.name, TopicORM.name)
        .all()
    )
    return pd.DataFrame(rows, columns=["Dimension", "Theme", "TopicID", "Topic"])

def upsert_assessment_session(s: Session, name: str, assessor: Optional[str], organization: Optional[str], notes: Optional[str]):
    return SessionRepo(s).create(name=name, assessor=assessor, organization=organization, notes=notes)

def record_rating(s: Session, session_id: int, topic_id: int, cmmi_level: Optional[int], is_na: bool, comment: Optional[str] = None):
    return EntryRepo(s).upsert(session_id=session_id, topic_id=topic_id, rating_level=cmmi_level, is_na=is_na, comment=comment)

def compute_theme_averages(s: Session, session_id: int):
    return ScoringService(s).compute_theme_averages(session_id)

def compute_dimension_averages(s: Session, session_id: int):
    return ScoringService(s).compute_dimension_averages(session_id)

def export_results(s: Session, session_id: int):
    # return two DataFrames
    topics = list_dimensions_with_topics(s)
    entries = s.query(AssessmentEntryORM).filter_by(session_id=session_id).all()
    rows = []
    for e in entries:
        rows.append({"TopicID": e.topic_id, "Rating": e.rating_level, "N/A": e.is_na, "Comment": e.comment, "CreatedAt": e.created_at})
    entries_df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["TopicID", "Rating", "N/A", "Comment", "CreatedAt"])
    return topics, entries_df

def combine_sessions_to_master(s: Session, source_session_ids: list[int], name: str, assessor: Optional[str]=None, organization: Optional[str]=None, notes: Optional[str]=None):
    """Create a new 'master' session by averaging topic scores across the selected source sessions.
    - Excludes N/A entries.
    - Uses computed_score (decimal) to preserve precision.
    - If a topic has no ratings across all sources, it is marked N/A.
    """
    if not source_session_ids:
        raise ValueError("No source sessions provided.")

    # Create master session
    master = upsert_assessment_session(s, name=name, assessor=assessor, organization=organization, notes=notes)

    # Build list of topic IDs
    from ..infrastructure.models import TopicORM, AssessmentEntryORM
    topic_ids = [tid for (tid,) in s.query(TopicORM.id).all()]

    # Index entries for source sessions by topic
    from collections import defaultdict
    by_topic: dict[int, list[float]] = defaultdict(list)

    entries = s.query(AssessmentEntryORM).filter(AssessmentEntryORM.session_id.in_(source_session_ids)).all()
    for e in entries:
        if e.is_na:
            continue
        val = e.computed_score if e.computed_score is not None else e.rating_level
        if val is not None:
            by_topic[e.topic_id].append(float(val))

    # Write master entries
    from ..infrastructure.repositories import EntryRepo
    er = EntryRepo(s)
    for tid in topic_ids:
        vals = by_topic.get(tid, [])
        if vals:
            avg = sum(vals) / len(vals)
            er.upsert(session_id=master.id, topic_id=tid, rating_level=None, is_na=False, comment=None)
            # set computed_score manually (since repo doesn't take it yet)
            me = s.query(AssessmentEntryORM).filter_by(session_id=master.id, topic_id=tid).one()
            me.computed_score = round(avg, 2)
        else:
            er.upsert(session_id=master.id, topic_id=tid, rating_level=None, is_na=True, comment=None)

    s.flush()
    return master
