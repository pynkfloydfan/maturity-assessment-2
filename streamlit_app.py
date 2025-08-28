from __future__ import annotations
from pathlib import Path
import math
from typing import Optional

import streamlit as st

# Infra config
from app.infrastructure.db import DBConfig

# UI modules
from app.ui import styles
from app.ui.sidebar import build_sidebar
from app.ui.rate_topics import build_rate_topics
from app.ui.dashboard import build_dashboard


def load_default_cfg_from_secrets() -> DBConfig:
    """Read DB defaults from Streamlit secrets."""
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


def main() -> None:
    st.set_page_config(
        page_title=st.secrets.get("app", {}).get("title", "Resilience Assessment"),
        layout="wide",
    )
    styles.inject()

    default_cfg = load_default_cfg_from_secrets()
    cfg, engine, SessionLocal = build_sidebar(default_cfg)

    if st.session_state.get("db_uninitialized"):
        st.info("No database found. Please initialise the database first.")
        return

    st.title(st.secrets.get("app", {}).get("title", "Operational Resilience Maturity Assessment"))

    tabs = st.tabs(["① Rate topics", "② Dashboard"])
    with tabs[0]:
        build_rate_topics(SessionLocal)
    with tabs[1]:
        build_dashboard(SessionLocal)


if __name__ == "__main__":
    main()
