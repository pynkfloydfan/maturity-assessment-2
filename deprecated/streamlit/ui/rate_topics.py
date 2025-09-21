from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker

from app.application.api import record_topic_rating as record_rating
from app.infrastructure.models import AssessmentEntryORM, RatingScaleORM
from app.ui.cache import cached_explanations_for, cached_topics_df
from app.ui.components import topic_card
from app.ui.state_keys import DB_URL, FOCUSED_TOPIC_ID, SESSION_ID

RATING_OPTIONS = ["N/A", 1, 2, 3, 4, 5]


def build_rate_topics(session_factory: sessionmaker[Session]) -> None:
    """Rate topics page: sticky toolbar selectors + card stack + single guidance drawer."""
    session_id = st.session_state.get(SESSION_ID)
    if not session_id:
        st.info("Select or create a session from the sidebar to begin rating.")
        return

    db_url = st.session_state.get(DB_URL, "")
    df_all = cached_topics_df(session_factory, db_url)

    # Sticky mini-toolbar: Dimension + Theme + crumb/pill
    st.markdown('<div class="mini-toolbar">', unsafe_allow_html=True)
    c_dim, c_theme, c_meta = st.columns([1, 1, 1])

    with c_dim:
        dims = ["— Select —"] + sorted(df_all["Dimension"].unique().tolist())
        dim = st.selectbox(
            "Dimension", dims, index=0, key="ui_dim_select", label_visibility="collapsed"
        )
        st.caption("Dimension")

    with c_theme:
        if dim == "— Select —":
            df_dim = df_all  # placeholder
            themes = ["— Select —"]
        else:
            df_dim = df_all[df_all["Dimension"] == dim]
            themes = ["— Select —"] + sorted(df_dim["Theme"].unique().tolist())
        theme = st.selectbox(
            "Theme", themes, index=0, key="ui_theme_select", label_visibility="collapsed"
        )
        st.caption("Theme")

    with c_meta:
        crumbs_ph = st.empty()
        pill_ph = st.empty()

    st.markdown("</div>", unsafe_allow_html=True)

    if dim == "— Select —":
        st.info("Choose a Dimension to continue.")
        return

    if theme == "— Select —":
        crumbs_ph.markdown(f'<div class="crumbs">{dim}</div>', unsafe_allow_html=True)
        st.info("Choose a Theme to start rating topics.")
        return

    # Selected theme topics
    df = df_dim[df_dim["Theme"] == theme]
    topic_ids_in_view = df["TopicID"].astype(int).tolist()
    if not topic_ids_in_view:
        crumbs_ph.markdown(f'<div class="crumbs">{dim} › {theme}</div>', unsafe_allow_html=True)
        pill_ph.markdown("")
        st.info("No topics match the current selection.")
        return

    # Prefetch entries + rating labels
    with session_factory() as s:
        entries = (
            s.query(AssessmentEntryORM)
            .filter(
                AssessmentEntryORM.session_id == session_id,
                AssessmentEntryORM.topic_id.in_(topic_ids_in_view),
            )
            .all()
        )
        current_by_tid = {e.topic_id: e for e in entries}
        {r.level: r.label for r in s.query(RatingScaleORM).order_by(RatingScaleORM.level)}

    guidance_index = cached_explanations_for(session_factory, db_url, tuple(topic_ids_in_view))

    # Progress (N/A does not count)
    def current_ui_or_db_rating(tid: int) -> int | None:
        key = f"rating_{tid}"
        if key in st.session_state and isinstance(st.session_state[key], int):
            return int(st.session_state[key])
        e = current_by_tid.get(tid)
        if e and (not e.is_na) and e.rating_level is not None:
            return int(e.rating_level)
        return None

    rated_count = sum(1 for tid in topic_ids_in_view if current_ui_or_db_rating(tid) is not None)
    total_topics = len(topic_ids_in_view)
    pct = (rated_count / total_topics) * 100 if total_topics else 0.0

    crumbs_ph.markdown(f'<div class="crumbs">{dim} › {theme}</div>', unsafe_allow_html=True)
    pill_ph.markdown(f'<div class="pill">{pct:.0f}% topics rated</div>', unsafe_allow_html=True)

    # Layout: cards + drawer
    left, right = st.columns([2, 1], gap="large")

    # Focused topic for the guidance drawer
    if (
        FOCUSED_TOPIC_ID not in st.session_state
        or int(st.session_state[FOCUSED_TOPIC_ID]) not in topic_ids_in_view
    ):
        st.session_state[FOCUSED_TOPIC_ID] = int(topic_ids_in_view[0])

    with left:
        # Unrated first, then by Topic
        def sort_key(row):
            tid = int(row["TopicID"])
            return 0 if current_ui_or_db_rating(tid) is None else 1

        df_sorted = df.sort_values(by="Topic").sort_values(
            by="TopicID",
            key=lambda col: [sort_key(df.loc[df["TopicID"] == x].iloc[0]) for x in col],
        )

        for _, r in df_sorted.iterrows():
            tid = int(r["TopicID"])
            entry = current_by_tid.get(tid)

            # Defaults: UI value → DB value → "N/A"
            if f"rating_{tid}" in st.session_state:
                default_val = st.session_state[f"rating_{tid}"]
            elif entry and not entry.is_na and entry.rating_level is not None:
                default_val = int(entry.rating_level)
            else:
                default_val = "N/A"

            default_comment = st.session_state.get(
                f"comment_{tid}", (entry.comment if entry and entry.comment else "")
            )

            topic_card(
                topic_id=tid,
                topic_title=str(r["Topic"]),
                default_value=default_val,
                default_comment=default_comment,
                guidance_index=guidance_index,
                rating_key=f"rating_{tid}",
                comment_key=f"comment_{tid}",
                on_focus_key=FOCUSED_TOPIC_ID,
            )

        # Save-all button writes only UI-touched topics/comments; others remain unchanged
        if st.button("💾 Save assessment (all topics)", key="save_assessment_all"):
            with session_factory() as s2:
                df_all_topics = cached_topics_df(session_factory, db_url)
                for _, rr in df_all_topics.iterrows():
                    ttid = int(rr["TopicID"])
                    rating_key = f"rating_{ttid}"
                    comment_key = f"comment_{ttid}"
                    if rating_key not in st.session_state and comment_key not in st.session_state:
                        continue
                    val = st.session_state.get(rating_key, "N/A")
                    comment_val = st.session_state.get(comment_key, None)
                    if val == "N/A":
                        is_na, cmmi = True, None
                    else:
                        is_na, cmmi = False, int(val)
                    record_rating(
                        s2,
                        session_id=session_id,
                        topic_id=ttid,
                        rating_level=cmmi,
                        is_na=is_na,
                        comment=comment_val or None,
                    )
                s2.commit()
            cached_topics_df.clear()
            cached_explanations_for.clear()
            st.success("Assessment saved.")

    with right:
        st.markdown(
            '<aside class="drawer" role="region" aria-label="Full guidance">',
            unsafe_allow_html=True,
        )
        focus_tid = int(st.session_state[FOCUSED_TOPIC_ID])
        title = df[df["TopicID"] == focus_tid]["Topic"].iloc[0]
        st.markdown(f"<h2>Full guidance — {title}</h2>", unsafe_allow_html=True)

        # Highlight current selected level
        current_val = st.session_state.get(f"rating_{focus_tid}", None)
        if not isinstance(current_val, int):
            ee = current_by_tid.get(focus_tid)
            current_val = (
                int(ee.rating_level)
                if ee and not ee.is_na and ee.rating_level is not None
                else None
            )

        for lvl in [1, 2, 3, 4, 5]:
            bullets = guidance_index.get(focus_tid, {}).get(lvl, [])
            if not bullets:
                continue
            from app.infrastructure.models import RatingScaleORM as _RatingScaleORM

            with session_factory() as s3:
                rating = s3.get(_RatingScaleORM, lvl)
                label = rating.label if rating else str(lvl)
            css_class = "level-title is-current" if current_val == lvl else "level-title"
            st.markdown(f'<h3 class="{css_class}">{lvl} — {label}</h3>', unsafe_allow_html=True)
            for b in bullets[:10]:
                st.markdown(f"- {b}")
        st.markdown("</aside>", unsafe_allow_html=True)
