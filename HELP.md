# Help & User Guide

## Contents
- [Introduction](#introduction)
- [Quick Start Checklist](#quick-start-checklist)
- [Application Navigation](#application-navigation)
- [Working with Sessions](#working-with-sessions)
- [Dashboard Insights](#dashboard-insights)
- [Database Configuration](#database-configuration)
- [Seeding & Maintaining Data](#seeding--maintaining-data)
- [Uploading Assessments from Excel](#uploading-assessments-from-excel)
- [Exporting Assessment Results](#exporting-assessment-results)
- [Command-Line Utilities](#command-line-utilities)
- [Troubleshooting & FAQs](#troubleshooting--faqs)
- [Reference Appendix](#reference-appendix)

---

## Introduction
The Operational Resilience Maturity Assessment platform combines a FastAPI backend, a React/Vite frontend, and a SQL database (SQLite by default, MySQL optional) to help teams capture, analyse, and report on CMMI-aligned assessments. This guide distils the technical capabilities documented in the codebase into practical, user-friendly instructions for administrators and assessors.

## Quick Start Checklist
1. **Install dependencies**: `poetry install` for backend tooling, `npm install` (inside `frontend/`) for the React bundle.
2. **Configure the database** via **Settings → Database configuration** (or by supplying the `DB_` environment variables listed below).
3. **Initialise schema**: click **Initialise tables** in Settings or run `poetry run alembic upgrade head` to apply migrations.
4. **Seed the enhanced dataset** using the Settings page or `poetry run seed-database` (defaults to `app/source_data/Maturity_Assessment_Data.xlsx`).
5. **Create a session** from **Settings → Sessions** so the dashboard has context.
6. **Capture ratings** in the main UI, or import them from Excel (details in [Uploading Assessments from Excel](#uploading-assessments-from-excel)).
7. **Review dashboards** via the “Dashboard” tab, and export results as JSON/XLSX when needed.

## Application Navigation
- **Header**: Select the active session (required before dashboards load) and access key routes.
- **Dashboard**: Visualises scores through heatmap tiles, radar plots, and numerical summaries.
- **Settings**: Administrative hub for database configuration, seeding, session management, and uploads.
- **Static Assets**: Served from `app/web/static/`, including the Excel template referenced in this guide.

## Working with Sessions
### Creating Sessions
- Navigate to **Settings → Sessions → Create session**.
- Provide at least a name; assessor, organisation, and notes are optional.
- Successful creation triggers a toast-style confirmation and refreshes the session list.

### Selecting Sessions
- Use the session selector in the page header. The ID displayed on the dashboard (e.g., `#12`) confirms the active context.

### Combining Sessions
- Still in **Settings → Sessions**, multi-select source sessions and give the combined session a name.
- The backend averages non-N/A ratings across sources and stores the result as a brand-new session.

### Editing Ratings
- Change values directly via the main assessment pages or use the [Excel upload workflow](#uploading-assessments-from-excel) for bulk updates.

## Dashboard Insights
The dashboard is split into two tabbed panels powered by `/api/sessions/{id}/dashboard` and `/dashboard/figures` endpoints.

### Maturity Heatmap
- Displays one tile per dimension with gradient colouring (see `useDashboard` hook and `DashboardPage.tsx`).
- Each tile exposes average score, coverage, and quick status copy.

### Radar Plot
- Uses `app/utils/resilience_radar.py` to generate a radar figure with theme mini-bars around each dimension spoke.
- Auto-resizes and sits inside a softly coloured container for clarity.

### Summary Metrics
- Top cards show active session, tile count, and aggregated coverage/score metrics computed by the `useDashboard` hook.

## Database Configuration
Settings for the backend live in `app/infrastructure/config.py` and the `.env` file.

### Environment Variables
| Variable | Purpose | Notes |
| --- | --- | --- |
| `DB_BACKEND` | `sqlite` (default) or `mysql` | Controls which block below applies |
| `DB_SQLITE_PATH` | Path to the SQLite file | Defaults to `./resilience.db` |
| `DB_MYSQL_HOST` | MySQL hostname | Required for MySQL |
| `DB_MYSQL_PORT` | Port (int) | Default `3306` |
| `DB_MYSQL_USER` | Username | Required for MySQL |
| `DB_MYSQL_PASSWORD` | Password | Optional but typically needed |
| `DB_MYSQL_DATABASE` | Database name | Required for MySQL |
| `DB_MYSQL_CHARSET` | Charset, default `utf8mb4` | Rarely changed |
| `DB_POOL_PRE_PING`, `DB_POOL_RECYCLE`, `DB_ECHO` | Connection tuning flags | Optional |

### Settings Page Controls
- **Save configuration** persists the entries to the FastAPI settings model for the current runtime.
- **Initialise tables** calls `/api/settings/database/init`, creating tables if absent.
- **Seed from Excel** hits `/api/settings/database/seed` and streams CLI output to the UI (shown under the button when available).

## Seeding & Maintaining Data
- The canonical workbook is `app/source_data/Maturity_Assessment_Data.xlsx`.
- Seeding populates dimensions, themes, topics, rating scale, and guidance text (see `scripts/seed_dataset.py`).
- Re-running the seed script updates descriptions, replaces per-topic explanations, and preserves IDs, so it’s safe after schema adjustments.
- Use **Refresh sessions** in Settings to fetch new or updated sessions once seeding completes.

## Uploading Assessments from Excel
### Template
- Download `/static/templates/assessment_upload_template.xlsx`. It mirrors the export format with a single sheet named `Assessment`.

### Required Columns
| Column | Required? | Behaviour |
| --- | --- | --- |
| `TopicID` | Yes | Must match an existing topic ID. Rows with missing/invalid IDs fail. |
| `Rating` | Optional | Parsed as integers 1–5; invalid values raise validation errors. |
| `ComputedScore` | Optional | Parsed as decimal; ignored if blank. |
| `N/A` | Optional | Treated as boolean (`true`, `yes`, `1`, etc.). If true, rating & computed score are ignored. |
| `Comment` | Optional | Trimmed and stored verbatim; empty strings become `None`. |
| Other columns | Optional | Ignored during import but kept in the template for context. |

### Upload Workflow
1. Go to **Settings → Upload assessment**.
2. Choose the target session (defaults to the newest one when the page loads).
3. Select the Excel file (`.xlsx` recommended).
4. Click **Upload assessment**. The button disables until a file is chosen.
5. Success response: “Imported *X* entries.” The system upserts ratings/comments via the same logic as manual edits.
6. Validation failure: errors are listed with row numbers and field messages. No data is written when errors occur.

### What Gets Updated
- Only rows with a valid `TopicID` and at least one of (`Rating`, `ComputedScore`, `N/A`, `Comment`) set.
- Existing entries are updated; missing entries are created automatically.

## Exporting Assessment Results
- **JSON Export** `/api/sessions/{id}/exports/json`: mirrors the API payload structure (`topics` and `entries` arrays).
- **XLSX Export** `/api/sessions/{id}/exports/xlsx`: now produces a single worksheet named `Assessment` joining topics and entries on `TopicID`. Empty values remain blank for easy filtering.
- Exports are surfaced in the dashboard toolbar buttons and can be retrieved programmatically via the endpoints.

## Command-Line Utilities
- `poetry run seed-database`: Wrapper around `scripts/seed_dataset.py`; accepts flags for backend, paths, and MySQL credentials (aliases `--mysql-database` and legacy `--mysql-db`).
- `poetry run server`: Runs `scripts/run_server.py`, ensuring the React build (`npm run build`) exists before launching Uvicorn in reload mode.
- Direct invocation: `poetry run uvicorn app.web.main:app --reload` if you prefer manual frontend build management.

## Troubleshooting & FAQs
### “Select a session” banner on the dashboard
- No session is active. Use the header dropdown or create one in Settings.

### “Failed to seed database” or validation errors
- Check `.env` values or the seed output shown in the Settings page. Legacy `MYSQL_*` environment variables are still read for backwards compatibility, but the recommended naming uses `DB_` prefixes.

### Excel import failed with validation errors
- Ensure every row has a valid `TopicID`. Ratings must be integers 1–5, computed scores must be numeric, and boolean columns use clear true/false indicators.
- The error list includes row numbers (Excel rows start at 2 in the message because 1 is the header).

### Dashboard returns a 400/500 error
- Confirm the session exists and contains ratings. The backend logs (configured via `app/infrastructure/logging.py`) will detail root causes. Look in `logs/` if file logging is enabled.

### Frontend isn’t serving updated assets
- Run `npm run build` in `frontend/`. The server auto-detects missing manifests and triggers a rebuild when started via `poetry run server`.

## Reference Appendix
- **Backend configuration**: `app/infrastructure/config.py` (`DatabaseConfig`, `ApplicationConfig`, `StreamlitConfig` retained only for backwards compatibility tests).
- **Repositories**: `app/infrastructure/repositories_*` handle database CRUD for sessions, topics, entries, etc.
- **Web API**: `app/web/routes/api.py` exposes REST endpoints consumed by the frontend and external integrations.
- **Template location**: `app/web/static/templates/assessment_upload_template.xlsx`.
- **Frontend dashboard**: `frontend/src/components/DashboardPage.tsx`, `frontend/src/hooks/useDashboard.ts`.
- **Settings UI**: `frontend/src/components/SettingsPage.tsx` (includes upload, seeding, session management logic).
- **Export logic**: `app/utils/exports.py` (single-sheet XLSX builder), `app/utils/resilience_radar.py` (chart helpers).
- **Tests**: `tests/test_dashboard_api.py`, `tests/test_improvements.py` cover API contracts and configuration guards.

For deeper technical customisation, review the corresponding modules referenced above. This help guide can be linked directly from a “Help” or “Documentation” menu to give end users a complete operational playbook.

