from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from app.application.api import (
    compute_dimension_averages,
    compute_theme_averages,
    export_session_results as export_results,
    list_dimensions_with_topics,
)
from app.infrastructure.models import AssessmentEntryORM
from app.ui.components import scorecard
from app.ui.state_keys import SESSION_ID
from app.utils.exports import make_json_export_payload, make_xlsx_export_bytes
from app.utils.resilience_radar import gradient_color, make_resilience_radar_with_theme_bars


def build_dashboard(SessionLocal) -> None:
    session_id = st.session_state.get(SESSION_ID)
    if not session_id:
        st.info("Create/select a session on the 'Rate topics' tab to see results.")
        return

    with SessionLocal() as s:
        dim_avgs = compute_dimension_averages(s, session_id=session_id)
        compute_theme_averages(s, session_id=session_id)

        # ── Dimension averages + vertical legend (90/10)
        st.subheader("Dimension averages")
        left, right = st.columns([9, 1], gap="large")

        with left:
            cols = st.columns(3)
            for i, rec in enumerate(dim_avgs):
                try:
                    avg_val = float(rec.average) if rec.average is not None else float("nan")
                except Exception:
                    avg_val = float("nan")
                avg_str = "—" if math.isnan(avg_val) else f"{avg_val:.2f}"
                bg_hex = None if math.isnan(avg_val) else gradient_color(avg_val)
                subtitle = f"{rec.name} &nbsp; · &nbsp; coverage {rec.coverage*100:.0f}%"
                with cols[i % 3]:
                    scorecard(avg_str, subtitle, bg_hex=bg_hex)

        with right:
            # Vertical legend for 1..5 scale (top=1, bottom=5)
            st.markdown(
                """
                <style>
                .cb-wrap{ position:sticky; top:1rem; }
                .cb-row{ display:flex; gap:10px; align-items:stretch; }
                .cb-bar{
                position:relative;
                width: 24px;
                min-height: 320px;
                border-radius: 6px;
                border:1px solid #e5e7eb;
                /* top (1) = red, bottom (5) = green */
                background: linear-gradient(
                    to bottom,
                    #D73027 0%,
                    #D78827 25%,
                    #FEE08B 50%,
                    #27D730 75%,
                    #3027D7 100%
                );
                }
                .cb-ticks{
                position:relative;
                width: 28px;
                font-size: 12px;
                line-height: 1;
                color: var(--card-fg, #111);
                }
                .cb-tick{
                position:absolute;
                left:0;
                transform: translateY(-50%);
                }
                /* precise positions (1 at top, 5 at bottom) */
                .cb-tick.t1{ top: 0%; }
                .cb-tick.t2{ top: 25%; }
                .cb-tick.t3{ top: 50%; }
                .cb-tick.t4{ top: 75%; }
                .cb-tick.t5{ top: 100%; transform: translateY(-100%); } /* keep inside box */
                </style>
                <div class="cb-wrap">
                <div class="cb-row">
                    <div class="cb-bar" aria-hidden="true"></div>
                    <div class="cb-ticks" aria-hidden="true">
                    <div class="cb-tick t1">1 - Initial</div>
                    <div class="cb-tick t2">2 - Managed</div>
                    <div class="cb-tick t3">3 - Defined</div>
                    <div class="cb-tick t4">4 - Quantitative</div>
                    <div class="cb-tick t5">5 - Optimised</div>
                    </div>
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Radar + mini bars (tinted via the updated util)
        topics_df = list_dimensions_with_topics(s)
        entries = s.query(AssessmentEntryORM).filter_by(session_id=session_id, is_na=False).all()
        ratings_map = {}
        for e in entries:
            val = (
                float(e.computed_score)
                if getattr(e, "computed_score", None) is not None
                else e.rating_level
            )
            if val is not None:
                ratings_map[e.topic_id] = float(val)

        scores_rows = []
        for _, r in topics_df.iterrows():
            score = ratings_map.get(int(r["TopicID"]))
            if score is not None:
                scores_rows.append(
                    {
                        "Dimension": r["Dimension"],
                        "Theme": r["Theme"],
                        "Question": r["Topic"],
                        "Score": float(score),
                    }
                )
        scores_df = pd.DataFrame(scores_rows, columns=["Dimension", "Theme", "Question", "Score"])

        if scores_df.empty:
            st.warning("No ratings yet for this session.")
        else:
            fig = make_resilience_radar_with_theme_bars(scores_df)  # now tinted
            st.plotly_chart(fig, use_container_width=True)

        # ── Exports (unchanged)
        st.subheader("Export results")
        topics_df, entries_df = export_results(s, session_id=session_id)
        json_data = make_json_export_payload(session_id, topics_df, entries_df)
        st.download_button(
            "Download JSON",
            data=json_data,
            file_name=f"assessment_{session_id}.json",
            mime="application/json",
        )
        xlsx_bytes = make_xlsx_export_bytes(topics_df, entries_df)
        st.download_button(
            "Download XLSX",
            data=xlsx_bytes,
            file_name=f"assessment_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
