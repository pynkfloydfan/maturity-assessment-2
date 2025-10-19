# Operational Resilience Maturity Assessment

Modernised operational-resilience assessment platform built on **FastAPI** with a
React/Vite front end. The app lets assessors capture CMMI 1–5 topic ratings,
review guidance, and surface dashboards backed by a SQL database (SQLite or
MySQL).

## Highlights

- Session management now captures a `created_at` date (with default-today picker).
- Topic pages guard against losing work with an unsaved-changes confirmation modal.
- Acronyms from the seed spreadsheet render with dotted-underlined tooltips across the UI.
- Excel-driven seeding ingests all workbook tables (including acronyms) via a single command.
- Plotly radar + tiles are served as JSON from FastAPI and rendered client-side.

## Stack

- Python 3.10+
- FastAPI + Uvicorn (backend API & static serving)
- React 18 + Vite build (frontend bundle)
- SQLAlchemy ORM + Alembic migrations
- SQLite (default) or MySQL 5.6+ via PyMySQL driver
- Plotly for charts (JSON payloads rendered client-side)

## Project layout

```
app/
  application/         # service layer orchestrating repositories and domain models
  domain/              # dataclasses, validation schemas, and core business rules
  infrastructure/      # config, SQLAlchemy models, repositories, logging
  utils/               # backup/restore utilities and shared helpers
  web/                 # FastAPI entrypoint, routers, schemas, static asset glue
  source_data/         # enhanced operational resilience spreadsheet source
frontend/
  src/                 # React/Vite app (components, contexts, hooks, styling)
  package.json         # JavaScript workspace manifest
alembic/               # database migrations managed via Alembic
scripts/               # CLI helpers (`run_server.py`, `seed_dataset.py`, etc.)
tests/                 # pytest suite covering validation, repos, and API flows
new-ui-plan/           # design documentation and modernisation checklist
logs/                  # runtime/server logs created by helper scripts
```

The legacy Streamlit prototype has been removed; FastAPI + React is now the canonical flow.

## Quick start

### 1. Install Python dependencies (Poetry)

```bash
poetry install
poetry run python -V
```

### 2. Configure the database

Database settings live in `app/infrastructure/config.py` and default to a local
SQLite file (`./resilience.db`). To override (e.g., MySQL), set the relevant
environment variables or update your `.env` / config as needed.

#### Database environment variables

`DatabaseConfig` reads settings from environment variables prefixed with `DB_`. Configure:

- `DB_BACKEND` — `sqlite` (default) or `mysql`
- `DB_SQLITE_PATH` — path to the SQLite database file (when `DB_BACKEND=sqlite`)
- `DB_MYSQL_HOST`, `DB_MYSQL_PORT`, `DB_MYSQL_USER`, `DB_MYSQL_PASSWORD`, `DB_MYSQL_DATABASE` — connection details for MySQL (when `DB_BACKEND=mysql`)
- Optional: `DB_MYSQL_CHARSET` (defaults to `utf8mb4`), `DB_POOL_PRE_PING`, `DB_POOL_RECYCLE`, `DB_ECHO`

`.env.example` includes these keys, and the FastAPI UI under **Settings → Database** writes the same values into the running app state. The CLI seeding script also honours legacy `MYSQL_*` variables for backward compatibility.

### 3. Seed the database from the enhanced spreadsheet (optional for dev)

```bash
poetry run seed-database \
  --backend sqlite \
  --sqlite-path ./resilience.db \
  --excel-path app/source_data/enhanced_operational_resilience_maturity_v6.xlsx
```

MySQL example:

```bash
poetry run seed-database \
  --backend mysql \
  --mysql-host localhost \
  --mysql-port 3306 \
  --mysql-user resilience_user \
  --mysql-password '***' \
  --mysql-database resilience \
  --excel-path app/source_data/enhanced_operational_resilience_maturity_v6.xlsx
```

The seeding script inventories the workbook tables up front (printing sheet names
and ranges), then populates dimensions, themes, topics, explanations, theme-level
guidance, rating scales, and the new acronyms lookup powering UI tooltips.

### 4. Build the frontend (Node/Vite)

> Prerequisite: [Node.js](https://nodejs.org/) 18+ (ships with `npm`). Install it
> once; no JavaScript knowledge required.

```bash
cd frontend
npm install         # safe to re-run; fetches dependencies
npm run build       # emits bundle into app/web/static/frontend/
```

If `npm install` surfaces a low-severity vulnerability you can inspect it with
`npm audit`; it does not block the build.

Re-run `npm run build` whenever you change files under `frontend/`.
For iterative work you can also run `npm run dev` in parallel (or rely on
`poetry run server`, which triggers builds automatically when artefacts are missing).

### 5. Launch the application (one Poetry command)

From the project root:

```bash
poetry run server
```

(Equivalently, `poetry run python scripts/run_server.py`.) The helper will:

1. ensure the frontend bundle exists (runs `npm install`/`npm run build` if the
   manifest is missing);
2. start Uvicorn in reload mode at <http://127.0.0.1:8000>.

If you prefer to manage the build manually, you can start the server directly:

```bash
poetry run uvicorn app.web.main:app --reload
```

## Developer workflow

- **Frontend changes** → edit files in `frontend/`, run `npm run build`, then
  refresh the browser.
- **Backend/data changes** → edit Python files, the dev server reloads
  automatically.
- **Database migrations** → use Alembic (new migrations live under
  `alembic/versions/`).
- **Settings page** → the React UI now exposes database configuration, seeding,
  and session management under `/settings`.
- **Topic navigation** → any unsaved rating/comment changes prompt a modal
  (“Save changes” / “Don’t save changes”) if you navigate away.
- **Acronym hover states** → seeded acronyms render with a dotted underline and
  tooltip, so verify hover text when you introduce new abbreviations via the spreadsheet.

## Deployment notes & follow-up ideas

- The helper script `scripts/run_server.py` is the recommended entry point for
  local runs and container CMDs: it ensures the frontend bundle exists before
  starting Uvicorn.
- For container images, pre-run `npm install && npm run build` during the build
  step to bake the assets into `app/web/static/frontend/`.
- Plotly dashboards currently render the pre-existing radar + mini-bar view.
  Future iterations can reuse the stored generic theme guidance to surface
  contextual tips alongside the charts.

## Seeding & admin actions

The `/settings` page already exposes the core admin actions:

- switch between SQLite/MySQL backends;
- initialise tables via the ORM metadata;
- seed from the enhanced spreadsheet;
- upload ratings/comments from a structured Excel workbook (`Assessment` sheet joined on `TopicID`);
- create or combine assessment sessions.

Grab `/static/templates/assessment_upload_template.xlsx` as a starter workbook; it mirrors the
download format for quick round-trips.

CLI utilities (`scripts/seed_dataset.py`) remain available for automation or
headless environments.

### Resetting the development database

If migrations fail because existing tables are out of sync (e.g., you see
`sqlite3.OperationalError: table ... already exists`), you can wipe the local
SQLite file and rebuild the schema:

```bash
rm resilience.db                     # delete the dev database
poetry run alembic upgrade head      # recreate tables with the latest schema
```

Then reseed via the Settings page (or re-run `scripts/seed_dataset.py`).


## Tests

```bash
poetry run pytest -q
```

The suite exercises dashboard endpoints and verifies that seeding from
`app/source_data/enhanced_operational_resilience_maturity_v6.xlsx` populates the
new descriptive fields.

## Manual QA checklist

Perform these steps whenever you want a quick end-to-end verification:

1. `poetry run server`
2. Open <http://127.0.0.1:8000>
3. Navigate to **Settings** → seed the database (if empty) and create/select a session.
4. Visit **Dimensions**/**Themes**/**Topics** to capture ratings and comments.
5. Confirm the **Dashboard** renders tiles, the Plotly radar, and download links
   for JSON/XLSX exports.

### Customising imagery

- **Golden source** – Runtime card art is served from
  `app/web/static/images/dimensions/` and
  `app/web/static/images/themes/<dimension>/<theme>.jpg`. Replace those `.jpg`
  files (e.g. `governance-leadership.jpg`) with your own artwork and rerun
  `npm run build` (or `poetry run server`, which triggers a build if required).
- Theme cards fall back to their parent dimension image when a
  `themes/<dimension>/<theme>.jpg` variant is not provided.
- Colour tokens (CSS variables beginning with `--color-`) live near the top of
  `frontend/src/index.css`. Adjust these to personalise the palette and typography.

### Iconography & badges

- Lucide icons are curated via `frontend/src/icons.ts`. Import icon components
  from that module so the bundle only includes the symbols we actually render.
- Reusable card, badge, and status styles live in `frontend/src/index.css`
  (`.tile-card`, `.badge-soft`, `.status-card`, `.topic-card`). Extend those
  classes when adding new surfaces to keep shadows, corner radius, and hover
  treatments consistent.

## Next steps

- Address the remaining design deliverables in `new-ui-plan/design-enhancements.md`:
  - Documentation refresh & ongoing design notes (README/forums)
  - Visual polish (hover states, shadows, badge styling refinements)
  - Evaluate adding optional new icons/illustrations once assets are selected

## Questions or issues?

Open an issue or reach out with the specific command/output you’re seeing –
having both the Python and Node build steps in the README should keep the
workflow repeatable even if you only work in Python day to day.
