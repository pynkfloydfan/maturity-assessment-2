from __future__ import annotations

import pandas as pd
import streamlit as st

from app.application.api import list_dimensions_with_topics
from app.infrastructure.models import ExplanationORM


@st.cache_data(ttl=300, show_spinner=False)
def cached_topics_df(_SessionLocal, db_url: str) -> pd.DataFrame:
    """Return the topics dataframe keyed by DB URL."""
    with _SessionLocal() as s:
        return list_dimensions_with_topics(s)


@st.cache_data(ttl=300, show_spinner=False)
def cached_explanations_for(
    _SessionLocal, db_url: str, topic_ids: tuple[int, ...]
) -> dict[int, dict[int, list[str]]]:
    """{topic_id: {level: [bullets]}} for provided topic ids."""
    if not topic_ids:
        return {}
    with _SessionLocal() as s:
        rows = (
            s.query(ExplanationORM.topic_id, ExplanationORM.level, ExplanationORM.text)
            .filter(ExplanationORM.topic_id.in_(list(topic_ids)))
            .order_by(ExplanationORM.topic_id, ExplanationORM.level, ExplanationORM.id)
            .all()
        )
    out: dict[int, dict[int, list[str]]] = {}
    for tid, lvl, txt in rows:
        out.setdefault(int(tid), {}).setdefault(int(lvl), []).append(txt)
    return out
