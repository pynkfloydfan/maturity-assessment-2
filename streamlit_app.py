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

CSS += """
<style>
:root{
  --space-2:.5rem; --space-3:.75rem; --space-4:1rem; --space-6:1.5rem;
  --radius:12px; --brand:#204e8a; --muted:#666; --border:#e6e6e6;
}
.theme-picker { display:grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); margin-bottom: var(--space-4); }
.theme-picker fieldset { border:none; padding:0; margin:0; }
.radio-card { position:relative; display:flex; align-items:center; gap:.5rem; border:1px solid var(--border); border-radius:var(--radius); padding:var(--space-4); cursor:pointer; }
.radio-card input { position:absolute; inset:0; opacity:0; cursor:pointer; }
.radio-card:has(input:checked){ border-color: var(--brand); box-shadow:0 0 0 3px rgba(32,78,138,.15); }
.theme-workspace { display:grid; grid-template-columns: minmax(520px, 1fr) minmax(320px, 36%); gap: var(--space-4); align-items:start; }
.workspace-header { display:flex; align-items:center; justify-content:space-between; gap:var(--space-3); margin-bottom: var(--space-3); }
.topic-list { display:flex; flex-direction:column; gap: var(--space-3); }
.topic-card { border:1px solid var(--border); border-radius:var(--radius); padding: var(--space-4); background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.04); }
.topic-card h3 { margin:0 0 .5rem 0; font-size:1.05rem; }
.topic-card .hint { color: var(--muted); font-size:.9rem; margin:.25rem 0 0 0; }
.topic-card .actions { display:flex; gap: var(--space-2); align-items:center; }
.drawer { position:sticky; top:1rem; max-height:82vh; overflow:auto; border-left:1px solid #eee; padding-left: var(--space-4); }
.drawer h2 { margin-top:0; font-size:1.1rem; }
.level-title { margin:.75rem 0 .25rem; }
.level-title.is-current { font-weight:700; }
button:focus, .radio-card:focus-within, select:focus, textarea:focus { outline:3px solid rgba(32,78,138,.35); outline-offset:2px; }
.kbd-hint kbd { border:1px solid #ccc; border-bottom-width:2px; padding:0 .25rem; border-radius:4px; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.85em;}
</style>
"""

CSS += """
<style>
.mini-toolbar{
  position: sticky;
  top: 0;
  z-index: 1000;
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: .5rem .25rem .6rem;
  margin: 0 0 0.75rem 0;
}
.mini-toolbar .crumbs{ font-weight:600; }
.mini-toolbar .pill{
  background:#F4F4F4; border-radius:999px; padding:.25rem .6rem; font-size:.9rem; color:#222;
  white-space:nowrap; display:inline-block;
}
.mini-toolbar .spacer{ height:.25rem; }
</style>
"""

CSS += """
<style>
/* ---- Theme tokens (light default) ---- */
:root{
  --card-bg: #ffffff;
  --card-fg: #111827;      /* slate-900 */
  --card-sub: #6b7280;     /* slate-500 */
  --card-border: #e5e7eb;  /* slate-200 */
  --pill-bg: #F4F4F4;
  --pill-fg: #111827;
}

/* ---- Dark mode overrides ---- */
@media (prefers-color-scheme: dark){
  :root{
    --card-bg: #111827;    /* slate-900 */
    --card-fg: #f3f4f6;    /* slate-100 */
    --card-sub: #cbd5e1;   /* slate-300 */
    --card-border: #374151;/* slate-700 */
    --pill-bg: #1f2937;    /* slate-800 */
    --pill-fg: #f3f4f6;
  }
}

/* ---- Apply tokens to cards & pills ---- */
.score-card{
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  color: var(--card-fg); /* ensure text contrasts with background */
}
.score-val{
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--card-fg) !important; /* big number always visible */
}
.score-sub{
  color: var(--card-sub) !important;
  font-size: 0.85rem;
}
.progress-pill{
  background: var(--pill-bg);
  color: var(--pill-fg);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.85rem;
}
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


# ---------- Helper shows the current level's first bullet ----------
def guidance_preview_for(tid: int, level_or_na, guidance_index: dict[int, dict[int, list[str]]]) -> str:
    if isinstance(level_or_na, int):
        bullets = guidance_index.get(tid, {}).get(level_or_na, [])
        return f"{level_or_na} — {bullets[0]}" if bullets else ""
    return ""


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


# ---------- Cached data loaders for performance ----------
@st.cache_data(ttl=300, show_spinner=False)
def cached_topics_df(_SessionLocal, db_url: str) -> pd.DataFrame:
    # db_url is only used to make the cache key stable & DB-specific
    with _SessionLocal() as s:
        df = list_dimensions_with_topics(s)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def cached_explanations_for(
    _SessionLocal, db_url: str, topic_ids: tuple[int, ...]
) -> dict[int, dict[int, list[str]]]:
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


def guidance_preview_for(tid: int, level_or_na, guidance_index: dict[int, dict[int, list[str]]]) -> str:
    """Return first bullet for the *current* level; if N/A or no bullets, show empty string."""
    if isinstance(level_or_na, int):
        firsts = guidance_index.get(tid, {}).get(level_or_na, [])
        return f"{level_or_na} — {firsts[0]}" if firsts else ""
    # N/A → no preview text (stays clean)
    return ""

# ---------- Sidebar builder ----------
def build_sidebar(default_cfg: DBConfig):
    # ─────────────────────────────────────────────────────────
    # 1) Database & Dataset  (collapsible)
    # ─────────────────────────────────────────────────────────
    with st.sidebar.expander("① Database & Dataset", expanded=True):
        # Backend selection
        starting_backend_is_sqlite = 0 if default_cfg.backend == "sqlite" else 1
        backend_choice = st.radio(
            "Backend",
            ["sqlite", "mysql"],
            index=starting_backend_is_sqlite,
            horizontal=True,
            key="db_backend_choice",
        )

        # Build config from UI
        if backend_choice == "sqlite":
            sqlite_path = st.text_input(
                "SQLite path",
                value=default_cfg.sqlite_path or "./resilience.db",
                key="sqlite_path_input",
            )
            cfg = DBConfig(backend="sqlite", sqlite_path=sqlite_path)
        else:
            host = st.text_input("Host", value=default_cfg.mysql_host or "localhost")
            port = st.number_input(
                "Port", value=int(default_cfg.mysql_port or 3306), step=1
            )
            user = st.text_input("User", value=default_cfg.mysql_user or "root")
            pw = st.text_input(
                "Password", value=default_cfg.mysql_password or "", type="password"
            )
            dbname = st.text_input(
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
        st.session_state["db_url"] = url  # cache key for data loaders

        # Initialise DB
        if st.button("Initialise DB (create tables)", key="btn_init_db"):
            initialise_database(engine)
            st.success("Tables created or already exist.")

        # Single source of truth for Excel path
        excel_path = st.text_input(
            "Excel path",
            value="enhanced-operational-resilience-maturity-assessment.xlsx",
            key="excel_path_seed",
        )
        excel_path_resolved = Path(excel_path)

        # Seed from Excel
        if st.button("Seed from Excel", key="btn_seed"):
            rc, cmd_str, out, err = seed_database_from_excel(cfg, excel_path_resolved)
            st.code(cmd_str)
            st.text(out)
            if rc != 0:
                st.error(err or "Seeding failed.")
            else:
                st.success("Seed completed.")

    # ─────────────────────────────────────────────────────────
    # 2) Sessions & Assessment (collapsible)
    # ─────────────────────────────────────────────────────────
    with st.sidebar.expander("② Sessions & Assessment", expanded=True):
        sessions, db_uninitialized = fetch_sessions(SessionLocal)
        st.session_state["db_uninitialized"] = db_uninitialized

        if db_uninitialized:
            st.info("No database found. Please initialise the database first.")
        else:
            # Existing sessions
            if sessions:
                options = {f"#{x['id']} — {x['name']}": x["id"] for x in sessions}
                sel_label = st.selectbox(
                    "Existing sessions",
                    list(options.keys()),
                    index=0,
                    key="session_pick",
                )
                if st.button("Use selected session", key="btn_use_session"):
                    st.session_state["session_id"] = options[sel_label]
                    st.success(f"Using session {sel_label}")

                st.caption(f"Active: Session #{st.session_state.get('session_id','—')}")

            else:
                st.info("No sessions yet — create one below.")

            st.markdown("---")

            # Assessment Session (create / update)
            st.subheader("Create / Use Assessment")
            with st.form("session_form_sidebar", clear_on_submit=False):
                name = st.text_input("Session name", value="Baseline Assessment", key="form_name")
                assessor = st.text_input("Assessor (optional)", key="form_assessor")
                org = st.text_input("Organization (optional)", key="form_org")
                notes = st.text_input("Notes (optional)", key="form_notes")
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

            # Combine multiple sessions → master session
            st.markdown("---")
            with st.expander("Combine sessions → master session", expanded=False):
                from app.application.api import combine_sessions_to_master
                if sessions:
                    multi_labels = [f"#{x['id']} — {x['name']}" for x in sessions]
                    selected = st.multiselect(
                        "Source sessions", multi_labels, default=[], key="combine_sources"
                    )
                    name_master = st.text_input(
                        "Master session name",
                        value="Combined Assessment",
                        key="combine_name",
                    )
                    if st.button("Create master session", key="btn_create_master"):
                        source_ids = [
                            int(lbl.split("—")[0].strip()[1:]) for lbl in selected
                        ]
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
    """
    Rate topics UI: compact sticky toolbar for Dimension/Theme selection + breadcrumb/progress,
    card stack editor on the left, single guidance drawer on the right, and one Save button.
    Assumes sessions & DB controls live in the sidebar.
    """
    # ----- Session gating -----
    session_id = st.session_state.get("session_id")
    if not session_id:
        st.info("Select or create a session from the sidebar to begin rating.")
        return

    # ----- Sticky mini-toolbar (Dimension / Theme + crumb + progress) -----
    db_url = st.session_state.get("db_url", "")
    df_all = cached_topics_df(SessionLocal, db_url)

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
            themes = ["— Select —"]
            df_dim = df_all  # placeholder
        else:
            df_dim = df_all[df_all["Dimension"] == dim]
            themes = ["— Select —"] + sorted(df_dim["Theme"].unique().tolist())
        theme = st.selectbox(
            "Theme", themes, index=0, key="ui_theme_select", label_visibility="collapsed"
        )
        st.caption("Theme")

    # Placeholders we fill once we can compute crumb + progress
    with c_meta:
        crumbs_ph = st.empty()
        pill_ph = st.empty()

    st.markdown("</div>", unsafe_allow_html=True)

    # ---- Early exits keep the toolbar visible above ----
    if dim == "— Select —":
        st.info("Choose a Dimension to continue.")
        return

    if theme == "— Select —":
        crumbs_ph.markdown(f'<div class="crumbs">{dim}</div>', unsafe_allow_html=True)
        st.info("Choose a Theme to start rating topics.")
        return

    # ---- Build Theme view ----
    df = df_dim[df_dim["Theme"] == theme]
    topic_ids_in_view = df["TopicID"].astype(int).tolist()
    if not topic_ids_in_view:
        crumbs_ph.markdown(f'<div class="crumbs">{dim} › {theme}</div>', unsafe_allow_html=True)
        pill_ph.markdown("")
        st.info("No topics match the current selection.")
        return

    # Prefetch entries & labels
    with SessionLocal() as s:
        entries = (
            s.query(AssessmentEntryORM)
             .filter(
                 AssessmentEntryORM.session_id == session_id,
                 AssessmentEntryORM.topic_id.in_(topic_ids_in_view),
             )
             .all()
        )
        current_by_tid = {e.topic_id: e for e in entries}
        rating_labels = {
            r.level: r.label
            for r in s.query(RatingScaleORM).order_by(RatingScaleORM.level)
        }

    # Cached guidance lookup: {topic_id: {level: [bullets...]}}
    guidance_index = cached_explanations_for(
        SessionLocal, db_url, tuple(topic_ids_in_view)
    )

    # Progress (N/A does not count)
    def current_ui_or_db_rating(tid: int) -> Optional[int]:
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

    # Update toolbar crumb + pill now that we can compute them
    crumbs_ph.markdown(f'<div class="crumbs">{dim} › {theme}</div>', unsafe_allow_html=True)
    pill_ph.markdown(f'<div class="pill">{pct:.0f}% topics rated</div>', unsafe_allow_html=True)

    # ----- Layout: cards (left) + single guidance drawer (right) -----
    left, right = st.columns([2, 1], gap="large")

    # Manage focused topic ID for the drawer
    focused_key = "focused_topic_id"
    if focused_key not in st.session_state or int(st.session_state[focused_key]) not in topic_ids_in_view:
        st.session_state[focused_key] = int(topic_ids_in_view[0])

    with left:
        # Unrated-first ordering to speed completion
        def sort_key(row):
            tid = int(row["TopicID"])
            return 0 if current_ui_or_db_rating(tid) is None else 1

        # Sort by unrated first, then by Topic for stable order
        df_sorted = df.sort_values(by="Topic").sort_values(
            by="TopicID",
            key=lambda col: [sort_key(df.loc[df["TopicID"] == x].iloc[0]) for x in col],
        )

        for _, r in df_sorted.iterrows():
            tid = int(r["TopicID"])
            e = current_by_tid.get(tid)

            # Default selection: UI value → DB value → "N/A"
            if f"rating_{tid}" in st.session_state:
                default_val = st.session_state[f"rating_{tid}"]
            elif e and not e.is_na and e.rating_level is not None:
                default_val = int(e.rating_level)
            else:
                default_val = "N/A"

            # Single-line hint using current level's first bullet
            preview = guidance_preview_for(tid, default_val, guidance_index)

            with st.container(border=False):
                st.markdown(
                    f'<article class="topic-card" aria-labelledby="t{tid}">', unsafe_allow_html=True
                )
                st.markdown(f'<h3 id="t{tid}">{r["Topic"]}</h3>', unsafe_allow_html=True)

                c1, c2 = st.columns([1, 1])
                with c1:
                    st.markdown('<label for="rate">CMMI rating</label>', unsafe_allow_html=True)
                    st.select_slider(
                        "CMMI (N/A–5)",
                        options=RATING_OPTIONS,
                        value=default_val,
                        key=f"rating_{tid}",
                        help="Choose N/A if not applicable.",
                    )
                    if preview:
                        st.markdown(f'<p class="hint">{preview}</p>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<label for="comment">Comment</label>', unsafe_allow_html=True)
                    st.text_area(
                        "Comment",
                        value=st.session_state.get(
                            f"comment_{tid}", (e.comment if e and e.comment else "")
                        ),
                        key=f"comment_{tid}",
                        height=70,
                    )

                if st.button("Full guidance", key=f"focus_{tid}", help="Show full guidance at right"):
                    st.session_state[focused_key] = tid

                st.markdown("</article>", unsafe_allow_html=True)

        # Save all topics set in UI (across the dataset); untouched topics stay unchanged
        if st.button("💾 Save assessment (all topics)", key="save_assessment_all"):
            with SessionLocal() as s2:
                df_all_topics = cached_topics_df(SessionLocal, db_url)
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
                        cmmi_level=cmmi,
                        is_na=is_na,
                        comment=comment_val or None,
                    )
                s2.commit()
            # Clear caches so previews/coverage refresh immediately
            cached_topics_df.clear()
            cached_explanations_for.clear()
            st.success("Assessment saved.")

    with right:
        st.markdown(
            '<aside class="drawer" role="region" aria-label="Full guidance">', unsafe_allow_html=True
        )
        focus_tid = int(st.session_state[focused_key])
        title = df[df["TopicID"] == focus_tid]["Topic"].iloc[0]
        st.markdown(f"<h2>Full guidance — {title}</h2>", unsafe_allow_html=True)

        # Highlight the currently selected level (UI first, then DB)
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
            label = rating_labels.get(lvl, str(lvl))
            css_class = "level-title is-current" if current_val == lvl else "level-title"
            st.markdown(
                f'<h3 class="{css_class}">{lvl} — {label}</h3>', unsafe_allow_html=True
            )
            for b in bullets[:10]:
                st.markdown(f"- {b}")
        st.markdown("</aside>", unsafe_allow_html=True)


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
                avg = float(rec.average) if rec.average is not None else float('nan')
                val = "-" if math.isnan(avg) else f"{avg:.2f}"
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
