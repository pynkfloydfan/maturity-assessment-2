from __future__ import annotations

import io
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy.exc import OperationalError

from app.infrastructure.db import DBConfig, build_connection_url, make_engine_and_session
from app.infrastructure.models import (
    Base,
    AssessmentEntryORM,
    RatingScaleORM,
    ExplanationORM
)
from app.infrastructure.repositories import (
    SessionRepo,
)
from app.infrastructure.uow import UnitOfWork
from app.application.api import (
    list_dimensions_with_topics,
    upsert_assessment_session,
    record_rating,
    compute_dimension_averages,
    compute_theme_averages,
    export_results,
    # combine_sessions_to_master is imported lazily inside sidebar expander to avoid circulars in some runners
)
from app.utils.resilience_radar import make_resilience_radar_with_theme_bars

RATING_OPTIONS = ["N/A", 1, 2, 3, 4, 5]


# ---------- Page config & minimal inline CSS ----------
st.set_page_config(
    page_title=st.secrets.get("app", {}).get("title", "Resilience Assessment"),
    layout="wide",
)

CSS = """
<style>
:root { --gap: 0.6rem; }
.stAppMainBlockContainer { padding-top: 0.5rem; }
div.block-container { padding-top: 1rem; }
.score-card { background: #ffffff; border: 1px solid #e7e7e7; border-radius: 14px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.score-val { font-size: 2.2rem; font-weight: 700; }
.score-sub { color: #666; font-size: 0.85rem; }
.progress-pill { background:#F4F4F4; padding:4px 10px; border-radius:999px; font-size:0.85rem; }
.sticky { position: sticky; top: 0; z-index: 999; background: white; padding-bottom: 0.5rem; }
table { font-size: 0.9rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- Config / helpers ----------
def load_config_from_secrets() -> DBConfig:
    db = st.secrets.get("db", {})
    backend = db.get("backend", "sqlite")
    if backend == "mysql":
        mysql = db.get("mysql", {})
        return DBConfig(
            backend="mysql",
            mysql_host=mysql.get("host", "localhost"),
            mysql_port=int(mysql.get("port", 3306)),
            mysql_user=mysql.get("user", "root"),
            mysql_password=mysql.get("password", ""),
            mysql_db=mysql.get("database", "resilience"),
        )
    sqlite = db.get("sqlite", {})
    return DBConfig(backend="sqlite", sqlite_path=sqlite.get("path", "./resilience.db"))


def initialise_database(engine) -> None:
    Base.metadata.create_all(engine)


def seed_database_from_excel(cfg: DBConfig, excel_path: Path) -> tuple[int, str, str, str]:
    """
    Runs the seeding script as a subprocess to avoid importing heavy deps into the app process.
    Returns (returncode, cmd_str, stdout, stderr).
    """
    script = Path(__file__).parent / "scripts" / "seed_dataset.py"
    cmd = [sys.executable, str(script), "--backend", cfg.backend]
    if cfg.backend == "sqlite":
        cmd += ["--sqlite-path", cfg.sqlite_path or "./resilience.db"]
    else:
        cmd += [
            "--mysql-host",
            cfg.mysql_host or "localhost",
            "--mysql-port",
            str(cfg.mysql_port or 3306),
            "--mysql-user",
            cfg.mysql_user or "root",
            "--mysql-password",
            cfg.mysql_password or "",
            "--mysql-db",
            cfg.mysql_db or "resilience",
        ]
    cmd += ["--excel-path", str(excel_path)]
    cmd_str = " ".join(cmd)

    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, cmd_str, res.stdout, res.stderr


def fetch_sessions(SessionLocal) -> tuple[list[dict], bool]:
    """
    Fetches sessions as primitives. Returns (sessions, db_uninitialized_flag).
    """
    db_uninitialized = False
    sessions: list[dict] = []
    try:
        with UnitOfWork(SessionLocal).begin() as s:
            raw_sessions = SessionRepo(s).list()
            sessions = [{"id": sess.id, "name": sess.name} for sess in raw_sessions]
    except OperationalError as e:
        if "no such table" in str(e).lower():
            db_uninitialized = True
        else:
            raise
    return sessions, db_uninitialized

# ---------- Export helpers ----------
def normalize_df_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of df where any datetime-like values are converted to ISO 8601 strings.
    Leaves other values unchanged. NaT/NaN -> None.
    """
    from datetime import datetime, date

    def _convert_cell(x):
        if x is None:
            return None
        # pandas Timestamp
        if isinstance(x, pd.Timestamp):
            if pd.isna(x):
                return None
            return x.to_pydatetime().isoformat()
        # python datetime/date
        if isinstance(x, (datetime, date)):
            return x.isoformat()
        # Let JSON handle numbers/strings/bools; leave everything else as-is
        if isinstance(x, float) and pd.isna(x):
            return None
        return x

    out = df.copy()
    for col in out.columns:
        out[col] = out[col].map(_convert_cell)
    return out


def make_json_export_payload(session_id: int, topics_df: pd.DataFrame, entries_df: pd.DataFrame) -> str:
    """
    Build a JSON string (pretty-printed) with datetime-like fields normalized to ISO 8601.
    """
    topics_norm = normalize_df_for_json(topics_df)
    entries_norm = normalize_df_for_json(entries_df)

    payload = {
        "session_id": session_id,
        "topics": topics_norm.to_dict(orient="records"),
        "entries": entries_norm.to_dict(orient="records"),
    }
    return json.dumps(payload, indent=2)  # no default=str needed now


def make_xlsx_export_bytes(topics_df: pd.DataFrame, entries_df: pd.DataFrame) -> bytes:
    """
    Create an in-memory XLSX (bytes) with Topics and Entries sheets.
    """
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        topics_df.to_excel(writer, index=False, sheet_name="Topics")
        entries_df.to_excel(writer, index=False, sheet_name="Entries")
    return bio.getvalue()


# ---------- Sidebar builder ----------
def build_sidebar(default_cfg: DBConfig):
    st.sidebar.header("Database")

    # Backend selection
    starting_backend_is_sqlite = 0 if default_cfg.backend == "sqlite" else 1
    backend_choice = st.sidebar.radio(
        "Backend",
        ["sqlite", "mysql"],
        index=starting_backend_is_sqlite,
        horizontal=True,
        key="db_backend_choice",
    )

    # Build config from UI
    if backend_choice == "sqlite":
        sqlite_path = st.sidebar.text_input(
            "SQLite path",
            value=default_cfg.sqlite_path or "./resilience.db",
            key="sqlite_path_input",
        )
        cfg = DBConfig(backend="sqlite", sqlite_path=sqlite_path)
    else:
        host = st.sidebar.text_input("Host", value=default_cfg.mysql_host or "localhost")
        port = st.sidebar.number_input(
            "Port", value=int(default_cfg.mysql_port or 3306), step=1
        )
        user = st.sidebar.text_input("User", value=default_cfg.mysql_user or "root")
        pw = st.sidebar.text_input(
            "Password", value=default_cfg.mysql_password or "", type="password"
        )
        dbname = st.sidebar.text_input(
            "Database", value=default_cfg.mysql_db or "resilience"
        )
        cfg = DBConfig(
            backend="mysql",
            mysql_host=host,
            mysql_port=int(port),
            mysql_user=user,
            mysql_password=pw,
            mysql_db=dbname,
        )

    # Engine & Session factory
    url = build_connection_url(cfg)
    engine, SessionLocal = make_engine_and_session(url)

    # Initialise DB
    if st.sidebar.button("Initialise DB (create tables)", key="btn_init_db"):
        initialise_database(engine)
        st.sidebar.success("Tables created or already exist.")

    # Single source of truth for Excel path (avoid duplicate keys)
    excel_path = st.sidebar.text_input(
        "Excel path",
        value="enhanced-operational-resilience-maturity-assessment.xlsx",
        key="excel_path_seed",
    )
    excel_path_resolved = Path(excel_path)

    # Seed from Excel
    if st.sidebar.button("Seed from Excel", key="btn_seed"):
        rc, cmd_str, out, err = seed_database_from_excel(cfg, excel_path_resolved)
        st.sidebar.code(cmd_str)
        st.sidebar.text(out)
        if rc != 0:
            st.sidebar.error(err or "Seeding failed.")
        else:
            st.sidebar.success("Seed completed.")

    # Sessions panel
    st.sidebar.markdown("---")
    st.sidebar.header("Sessions")

    sessions, db_uninitialized = fetch_sessions(SessionLocal)
    st.session_state["db_uninitialized"] = db_uninitialized

    if sessions:
        options = {f"#{x['id']} — {x['name']}": x["id"] for x in sessions}
        sel_label = st.sidebar.selectbox(
            "Select existing session", list(options.keys()), index=0, key="session_pick"
        )
        if st.sidebar.button("Use selected session", key="btn_use_session"):
            st.session_state["session_id"] = options[sel_label]
            st.sidebar.success(f"Using session {sel_label}")
    else:
        st.sidebar.info("No sessions yet — create one in 'Rate topics'.")

    with st.sidebar.expander("Combine multiple sessions → master session", expanded=False):
        # Lazy import here avoids issues in some packaging flows
        from app.application.api import combine_sessions_to_master

        if sessions:
            multi_labels = [f"#{x['id']} — {x['name']}" for x in sessions]
            selected = st.multiselect(
                "Source sessions", multi_labels, default=[], key="combine_sources"
            )
            name_master = st.text_input(
                "Master session name", value="Combined Assessment", key="combine_name"
            )
            if st.button("Create master session", key="btn_create_master"):
                source_ids = [
                    int(lbl.split("—")[0].strip()[1:]) for lbl in selected
                ]  # parse "#123 — Name"
                if not source_ids:
                    st.warning("Pick at least one source session.")
                else:
                    with UnitOfWork(SessionLocal).begin() as s:
                        master = combine_sessions_to_master(
                            s, source_session_ids=source_ids, name=name_master
                        )
                        st.session_state["session_id"] = master.id
                        st.success(
                            f"Created master session #{master.id}: {master.name} (now active)"
                        )
        else:
            st.info("No sessions available to combine.")

    return cfg, engine, SessionLocal


# ---------- Rate topics ----------
def build_rate_topics(SessionLocal) -> None:
    st.markdown('<div class="sticky">', unsafe_allow_html=True)
    with st.container():
        st.subheader("Assessment Session")
        with st.form("session_form", clear_on_submit=False):
            c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
            name = c1.text_input("Session name", value="Baseline Assessment")
            assessor = c2.text_input("Assessor (optional)")
            org = c3.text_input("Organization (optional)")
            notes = c4.text_input("Notes (optional)")
            submitted = st.form_submit_button("Create / Use Session")
        if submitted:
            with SessionLocal() as s:
                sess = upsert_assessment_session(
                    s,
                    name=name,
                    assessor=assessor,
                    organization=org,
                    notes=notes,
                )
                s.commit()
                st.session_state["session_id"] = sess.id
                st.success(f"Using session #{sess.id}: {sess.name}")
    st.markdown("</div>", unsafe_allow_html=True)

    session_id = st.session_state.get("session_id")
    if not session_id:
        st.info("Create or select an assessment session to begin rating.")
        return

    # Filters + grid
    with SessionLocal() as s:
        df_topics = list_dimensions_with_topics(s)

        dims = ["All"] + sorted(df_topics["Dimension"].unique().tolist())
        dim = st.selectbox("Dimension", dims, index=0, key="filter_dim")
        if dim != "All":
            df_topics = df_topics[df_topics["Dimension"] == dim]

        themes = ["All"] + sorted(df_topics["Theme"].unique().tolist())
        theme = st.selectbox("Theme", themes, index=0, key="filter_theme")
        if theme != "All":
            df_topics = df_topics[df_topics["Theme"] == theme]

        # Labels
        rating_labels = {
            r.level: r.label for r in s.query(RatingScaleORM).order_by(RatingScaleORM.level)
        }

        # Progress — N/A does NOT count as rated (2B)
        topic_ids_in_view = df_topics["TopicID"].astype(int).tolist()
        rated_count = 0
        for tid in topic_ids_in_view:
            key = f"rating_{tid}"
            if key in st.session_state:
                # counted only if 1..5 selected
                rated = st.session_state[key] in [1, 2, 3, 4, 5]
            else:
                # Fallback to DB if control never rendered yet
                cur = (
                    s.query(AssessmentEntryORM)
                    .filter_by(session_id=session_id, topic_id=tid)
                    .one_or_none()
                )
                rated = bool(cur and (not cur.is_na) and (cur.rating_level is not None))
            if rated:
                rated_count += 1
        total_topics = len(topic_ids_in_view)
        pct = (rated_count / total_topics) * 100 if total_topics else 0.0
        st.markdown(
            f'<span class="progress-pill">{pct:.0f}% topics rated (this view)</span>',
            unsafe_allow_html=True,
        )

        # Rating grid
        for _, row in df_topics.iterrows():
            with st.expander(f"🧩 {row['Topic']} — *{row['Theme']}*"):
                c1, c2 = st.columns([3, 1])

                # Guidance
                with c1:
                    from app.infrastructure.models import ExplanationORM
                    exps = (
                        s.query(ExplanationORM.level, ExplanationORM.text)
                        .filter(ExplanationORM.topic_id == int(row["TopicID"]))
                        .order_by(ExplanationORM.level, ExplanationORM.id)
                        .all()
                    )
                    if exps:
                        with st.expander("Show guidance (per level)", expanded=False):
                            prev_level = None
                            for level, text_ in exps:
                                if prev_level != level:
                                    st.markdown(
                                        f"**{level} — {rating_labels.get(level, str(level))}**"
                                    )
                                    prev_level = level
                                st.markdown(f"- {text_}")

                # Controls (single select_slider with N/A; remove checkbox and per-topic Save)
                with c2:
                    current = (
                        s.query(AssessmentEntryORM)
                        .filter_by(session_id=session_id, topic_id=int(row["TopicID"]))
                        .one_or_none()
                    )
                    if current and not current.is_na and current.rating_level is not None:
                        default_val = int(current.rating_level)
                    else:
                        default_val = "N/A"

                    st.select_slider(
                        "CMMI (N/A, 1–5)",
                        options=RATING_OPTIONS,
                        value=default_val,
                        key=f"rating_{int(row['TopicID'])}",
                    )
                    st.caption("Choose N/A or a CMMI level")

                    st.text_input(
                        "Comment (optional)",
                        value=current.comment if current and current.comment else "",
                        key=f"comment_{int(row['TopicID'])}",
                    )

    # --- Save all topics across the dataset in one go (1B) ---
    # This saves only the topics that have a UI value in session_state, so we don't
    # accidentally overwrite unseen topics. Existing DB values for untouched topics are preserved.
    if st.button("💾 Save assessment (all topics)", key="save_assessment_all"):
        with SessionLocal() as s2:
            # load all topics once, then write in a single transaction
            df_all = list_dimensions_with_topics(s2)
            for _, row in df_all.iterrows():
                tid = int(row["TopicID"])
                rating_key = f"rating_{tid}"
                comment_key = f"comment_{tid}"

                if rating_key not in st.session_state and comment_key not in st.session_state:
                    # user never visited/changed this topic; leave DB as-is
                    continue

                sel = st.session_state.get(rating_key, "N/A")
                comment_val = st.session_state.get(comment_key, None)

                if sel == "N/A":
                    is_na = True
                    rating_val = None
                else:
                    is_na = False
                    rating_val = int(sel)

                record_rating(
                    s2,
                    session_id=session_id,
                    topic_id=tid,
                    cmmi_level=rating_val,
                    is_na=is_na,
                    comment=comment_val or None,
                )
            s2.commit()
        st.success("Assessment saved (all topics that were set in the UI).")


# ---------- Dashboard ----------
def build_dashboard(SessionLocal) -> None:
    session_id = st.session_state.get("session_id")
    if not session_id:
        st.info("Create/select a session on the 'Rate topics' tab to see results.")
        return

    with SessionLocal() as s:
        dim_avgs = compute_dimension_averages(s, session_id=session_id)
        theme_avgs = compute_theme_averages(s, session_id=session_id)

        # Scorecards
        st.subheader("Dimension averages")
        cols = st.columns(3)
        for i, rec in enumerate(dim_avgs):
            with cols[i % 3]:
                val = "-" if math.isnan(rec.average) else f"{rec.average:.2f}"
                st.markdown(
                    f"""
                    <div class="score-card">
                        <div class="score-val">{val}</div>
                        <div class="score-sub">{rec.name} &nbsp; · &nbsp; coverage {rec.coverage*100:.0f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Radar + mini bars
        topics_df = list_dimensions_with_topics(s)

        # Prefer computed_score (decimals) when present; fallback to rating_level
        entries = (
            s.query(AssessmentEntryORM)
            .filter_by(session_id=session_id, is_na=False)
            .all()
        )
        ratings_map = {}
        for e in entries:
            val = float(e.computed_score) if getattr(e, "computed_score", None) is not None else e.rating_level
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
            fig = make_resilience_radar_with_theme_bars(scores_df)
            st.plotly_chart(fig, use_container_width=True)

        # Exports
        st.subheader("Export results")
        topics_df, entries_df = export_results(s, session_id=session_id)

        # JSON
        json_data = make_json_export_payload(session_id, topics_df, entries_df)
        st.download_button(
            "Download JSON",
            data=json_data,
            file_name=f"assessment_{session_id}.json",
            mime="application/json",
        )

        # XLSX
        xlsx_bytes = make_xlsx_export_bytes(topics_df, entries_df)
        st.download_button(
            "Download XLSX",
            data=xlsx_bytes,
            file_name=f"assessment_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ---------- App entry ----------
def main():
    # Sidebar (config + sessions + seed)
    default_cfg = load_config_from_secrets()
    cfg, engine, SessionLocal = build_sidebar(default_cfg)

    # Title
    st.title(st.secrets.get("app", {}).get("title", "Operational Resilience Maturity Assessment"))

    # Friendly guard for first-run / no-tables
    if st.session_state.get("db_uninitialized"):
        st.info("No database found, please initialise the database first")
        st.stop()

    # Tabs
    tabs = st.tabs(["① Rate topics", "② Dashboard"])
    with tabs[0]:
        build_rate_topics(SessionLocal)
    with tabs[1]:
        build_dashboard(SessionLocal)


if __name__ == "__main__":
    main()
