# New UI Migration Plan

## 1. Project scaffolding & tooling alignment
- [x] Document current entrypoints, dependencies, and scripts; decide FastAPI app layout under `app/web` (FastAPI app with `main.py`, `routes/`, `dependencies.py`; templates in `app/web/templates`; static assets served from `app/web/static/frontend`)
- [x] Introduce Vite-based frontend workspace by renaming the Figma bundle to `frontend/`, keeping Vite project root there, and configuring its build output to `app/web/static/frontend` via `vite.config.ts`
- [x] Update Poetry environment with FastAPI, templating, and static-serving deps via `poetry add fastapi uvicorn aiofiles jinja2 python-multipart`

## 2. Source data management & migrations
- [x] Move `Enhanced_Operational_Resilience_Maturity_v6.xlsx` into `app/source_data/enhanced_operational_resilience_maturity_v6.xlsx`
- [x] Design Alembic migration adding description fields (dimensions/themes/topics), image metadata columns, rating-scale descriptions, and new `theme_level_guidance` table (see `new-ui-plan/data-model-notes.md`)
- [x] Implement migration (`alembic/versions/619a67d956f6_add_descriptions_and_theme_guidance.py`) and SQLAlchemy model updates, leaving legacy spreadsheet in place until verification

## 3. Data ingestion utilities
- [x] Refactor `scripts/seed_dataset.py` and helpers to consume the new spreadsheet (richer tabs, optional metadata, new default path)
- [x] Add loader logic for theme-level generic definitions & CMMI level descriptions via new helpers in `scripts/seed_dataset.py`
- [x] Update caching layers and API functions to surface richer metadata via `list_dimensions_with_topics` (now returning descriptions and IDs)

## 4. Backend transition to FastAPI
- [x] Scaffold FastAPI application (ASGI entrypoint `app/web/main.py`, DB dependencies, static mount, base routers/templates)
- [x] Port assessment/session endpoints into REST/JSON handlers (`/api/dimensions`, `/api/themes`, `/api/sessions`, ratings, exports)
- [x] Implement responses powering Rate, Dashboard, and Settings flows (including session CRUD, combine, exports)

## 5. Frontend integration
- [x] Organise React components from Figma bundle into a Vite project (TypeScript, routing, state management)
- [x] Implement data fetching hooks for Dimensions ? Themes ? Topics ? Assessment flow using FastAPI endpoints
- [x] Recreate topic rating UI (cards, guidance drawer) with state persistence and save actions

## 6. Dashboard & charts
- [x] Expose Plotly figures (dimension tiles + radar with theme bars) as JSON via FastAPI endpoints
- [x] Render charts client-side using Plotly.js fed with server-generated JSON payloads
- [x] Ensure exports (JSON/XLSX) remain available via backend buttons / links

## 7. Settings & admin experience
- [x] Build persistent navigation with Settings page entry
- [x] Recreate DB backend selection, initialise tables, Excel seeding, session creation/combining within React UI
- [x] Add status messaging and validation consistent with previous Streamlit behaviour

## 8. Static asset pipeline
- [x] Rename Figma-provided images to match dimension names and host them locally within the package
- [x] Configure Vite build to emit assets into a FastAPI-served directory; ensure Docker guidance for building assets is clear
- [x] Add CI/test hooks to verify frontend build artefacts exist before packaging

## 9. Testing & QA
- [x] Update or add API-level tests for new FastAPI endpoints
- [x] Add seed-data verification test ensuring DB descriptions align with spreadsheet source of truth
- [x] Document manual end-to-end walkthrough covering Rate Topics workflow, dashboard, settings, and exports

## 10. Documentation & cleanup
- [x] Update `README.md` with architecture overview, setup (frontend build + FastAPI run), and migration guidance
- [x] Move Streamlit app + UI modules into `deprecated/` with README note
- [x] Provide deployment notes and outstanding follow-up ideas (e.g., using theme generics in UI)












