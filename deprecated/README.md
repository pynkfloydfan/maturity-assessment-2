# Deprecated Streamlit UI

The original Streamlit-based interface has been preserved here for reference.
Everything under `deprecated/streamlit/` is no longer part of the active
application runtime. Once the FastAPI + React rewrite is fully validated, this
folder can be removed.

Contents:

- `streamlit_app.py` – original entry point.
- `ui/` – Streamlit component helpers (sidebar, dashboard, rate topics, etc.).

All new development should target the FastAPI endpoints in `app/web/` and the
React frontend in `frontend/`.
