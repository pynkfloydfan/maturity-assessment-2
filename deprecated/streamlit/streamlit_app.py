from __future__ import annotations

from app.infrastructure.logging import setup_logging

# Show verbose logs in console while developing
setup_logging(
    level="DEBUG",  # <-- DEBUG here
    structured=False,  # readable console format
    enable_console=True,  # print to Streamlit terminal
    log_file="./logs/development.log",  # optional: also write a file
)
# --- end bootstrap ---

import streamlit as st

# Infra config - use the new configuration system
from app.infrastructure.config import DatabaseConfig, get_settings
from app.infrastructure.db import make_engine_and_session

# UI modules
from app.ui import styles
from app.ui.dashboard import build_dashboard
from app.ui.rate_topics import build_rate_topics
from app.ui.sidebar import build_sidebar


def load_database_config_from_secrets() -> DatabaseConfig:
    """Read DB configuration from Streamlit secrets and create DatabaseConfig."""
    db = st.secrets.get("db", {})
    backend = db.get("backend", "sqlite")

    if backend == "mysql":
        mysql = db.get("mysql", {})
        return DatabaseConfig(
            backend="mysql",
            mysql_host=mysql.get("host", "localhost"),
            mysql_port=int(mysql.get("port", 3306)),
            mysql_user=mysql.get("user", "root"),
            mysql_password=mysql.get("password", ""),
            mysql_database=mysql.get("database", "resilience"),
        )

    # SQLite configuration
    sqlite = db.get("sqlite", {})
    return DatabaseConfig(backend="sqlite", sqlite_path=sqlite.get("path", "./resilience.db"))


def get_streamlit_config():
    """Get Streamlit configuration from settings or secrets."""
    try:
        # Try to get from centralized settings first
        settings = get_settings()
        return settings.streamlit.get_streamlit_config()
    except Exception:
        # Fallback to secrets
        return {
            "page_title": st.secrets.get("app", {}).get("title", "Resilience Assessment"),
            "layout": "wide",
        }


def main() -> None:
    # Configure Streamlit page
    streamlit_config = get_streamlit_config()
    st.set_page_config(**streamlit_config)

    # Inject styles
    styles.inject()

    # Get database configuration
    try:
        db_config = load_database_config_from_secrets()
        engine, SessionLocal = make_engine_and_session(db_config.get_connection_url())

        # Store in session state for sidebar
        if "db_config" not in st.session_state:
            st.session_state.db_config = db_config
        if "engine" not in st.session_state:
            st.session_state.engine = engine
        if "SessionLocal" not in st.session_state:
            st.session_state.SessionLocal = SessionLocal

    except Exception as e:
        st.error(f"Database configuration error: {str(e)}")
        st.info("Please check your database configuration in .streamlit/secrets.toml")
        return

    # Build sidebar (updated to work with new config)
    cfg, engine, SessionLocal = build_sidebar(db_config)

    # Check if database needs initialization
    if st.session_state.get("db_uninitialized"):
        st.info("No database found. Please initialise the database first.")
        return

    # Main app title
    app_title = st.secrets.get("app", {}).get("title", "Operational Resilience Maturity Assessment")
    st.title(app_title)

    # Main application tabs
    tabs = st.tabs(["① Rate topics", "② Dashboard"])
    with tabs[0]:
        build_rate_topics(SessionLocal)
    with tabs[1]:
        build_dashboard(SessionLocal)


if __name__ == "__main__":
    main()
