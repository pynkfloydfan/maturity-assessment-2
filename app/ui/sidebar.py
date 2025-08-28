from __future__ import annotations
from pathlib import Path
from typing import Tuple, List, Dict

import streamlit as st
from sqlalchemy.exc import OperationalError

from app.infrastructure.db import DBConfig, build_connection_url, make_engine_and_session
from app.infrastructure.models import Base
from app.infrastructure.uow import UnitOfWork
from app.infrastructure.repositories import SessionRepo
from app.ui.state_keys import DB_URL, SESSION_ID
from app.utils.seed import initialise_database, seed_database_from_excel


def fetch_sessions(SessionLocal) -> tuple[List[Dict], bool]:
    """Return (sessions_as_primitives, db_uninitialized)."""
    try:
        with UnitOfWork(SessionLocal).begin() as s:
            raw = SessionRepo(s).list()
            sessions = [{"id": sess.id, "name": sess.name} for sess in raw]
        return sessions, False
    except OperationalError as e:
        if "no such table" in str(e).lower():
            return [], True
        raise


def build_sidebar(default_cfg: DBConfig):
    # ── ① Database & Dataset
    with st.sidebar.expander("① Database & Dataset", expanded=True):
        backend_choice = st.radio(
            "Backend",
            ["sqlite", "mysql"],
            index=0 if default_cfg.backend == "sqlite" else 1,
            horizontal=True,
            key="db_backend_choice",
        )

        if backend_choice == "sqlite":
            sqlite_path = st.text_input(
                "SQLite path",
                value=default_cfg.sqlite_path or "./resilience.db",
                key="sqlite_path_input",
            )
            cfg = DBConfig(backend="sqlite", sqlite_path=sqlite_path)
        else:
            host = st.text_input("Host", value=default_cfg.mysql_host or "localhost")
            port = st.number_input("Port", value=int(default_cfg.mysql_port or 3306), step=1)
            user = st.text_input("User", value=default_cfg.mysql_user or "root")
            pw = st.text_input("Password", value=default_cfg.mysql_password or "", type="password")
            dbname = st.text_input("Database", value=default_cfg.mysql_db or "resilience")
            cfg = DBConfig(
                backend="mysql", mysql_host=host, mysql_port=int(port), mysql_user=user, mysql_password=pw, mysql_db=dbname
            )

        url = build_connection_url(cfg)
        engine, SessionLocal = make_engine_and_session(url)
        st.session_state[DB_URL] = url

        if st.button("Initialise DB (create tables)", key="btn_init_db"):
            initialise_database(engine)
            st.success("Tables created or already exist.")

        excel_path = st.text_input(
            "Excel path",
            value="enhanced-operational-resilience-maturity-assessment.xlsx",
            key="excel_path_seed",
        )
        excel_resolved = Path(excel_path)

        if st.button("Seed from Excel", key="btn_seed"):
            rc, cmd_str, out, err = seed_database_from_excel(cfg, excel_resolved)
            st.code(cmd_str)
            st.text(out)
            if rc != 0:
                st.error(err or "Seeding failed.")
            else:
                st.success("Seed completed.")

    # ── ② Sessions & Assessment
    with st.sidebar.expander("② Sessions & Assessment", expanded=True):
        sessions, db_uninitialized = fetch_sessions(SessionLocal)
        st.session_state["db_uninitialized"] = db_uninitialized

        if db_uninitialized:
            st.info("No database found. Please initialise the database first.")
        else:
            if sessions:
                options = {f"#{x['id']} — {x['name']}": x["id"] for x in sessions}
                sel_label = st.selectbox(
                    "Existing sessions", list(options.keys()), index=0, key="session_pick"
                )
                if st.button("Use selected session", key="btn_use_session"):
                    st.session_state[SESSION_ID] = options[sel_label]
                    st.success(f"Using session {sel_label}")
                st.caption(f"Active: Session #{st.session_state.get(SESSION_ID, '—')}")
            else:
                st.info("No sessions yet — create one below.")

            st.markdown("---")

            # Create / Use assessment
            st.subheader("Create / Use Assessment")
            from app.application.api import upsert_assessment_session

            with st.form("session_form_sidebar", clear_on_submit=False):
                name = st.text_input("Session name", value="Baseline Assessment", key="form_name")
                assessor = st.text_input("Assessor (optional)", key="form_assessor")
                org = st.text_input("Organization (optional)", key="form_org")
                notes = st.text_input("Notes (optional)", key="form_notes")
                submitted = st.form_submit_button("Create / Use Session")

            if submitted:
                with SessionLocal() as s:
                    sess = upsert_assessment_session(
                        s, name=name, assessor=assessor, organization=org, notes=notes
                    )
                    s.commit()
                    st.session_state[SESSION_ID] = sess.id
                    st.success(f"Using session #{sess.id}: {sess.name}")

            st.markdown("---")
            with st.expander("Combine sessions → master session", expanded=False):
                from app.application.api import combine_sessions_to_master
                if sessions:
                    multi_labels = [f"#{x['id']} — {x['name']}" for x in sessions]
                    selected = st.multiselect("Source sessions", multi_labels, default=[], key="combine_sources")
                    name_master = st.text_input("Master session name", value="Combined Assessment", key="combine_name")
                    if st.button("Create master session", key="btn_create_master"):
                        source_ids = [int(lbl.split("—")[0].strip()[1:]) for lbl in selected]
                        if not source_ids:
                            st.warning("Pick at least one source session.")
                        else:
                            with UnitOfWork(SessionLocal).begin() as s:
                                master = combine_sessions_to_master(s, source_session_ids=source_ids, name=name_master)
                                st.session_state[SESSION_ID] = master.id
                                st.success(f"Created master session #{master.id}: {master.name} (now active)")
                else:
                    st.info("No sessions available to combine.")

    return cfg, engine, SessionLocal
