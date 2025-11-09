# Split-Pane Resilience Assessment Migration Plan

## Scope
- Replace the existing Themes and Topics pages with a single split-pane assessment view invoked after a dimension is selected.
- Persist dual maturity ratings (current & desired), comments, evidence links, and per-topic progress while enforcing business rules (desired ≥ current; N/A rules).
- Update backend schemas, migrations, and APIs; align seeds/fixtures; retire unused UI assets/styles/routes.

---

## Phase 1 – Data Model & Migration
1. Inspect current `assessment_entries` schema in `app/infrastructure/models.py` to confirm column names (`rating_level`, `is_na`, etc.) and constraints.
2. Design migration `alembic/versions/0004_split_pane_resilience_assessment.py`:
   - Rename `rating_level` → `current_maturity` and `is_na` → `current_is_na`.
   - Add nullable FK column `desired_maturity` referencing `rating_scale.level`.
   - Add boolean `desired_is_na` (default False, non-null), text `evidence_links` (JSON payload string), varchar `progress_state` (default `'not_started'`), and timestamp `updated_at` (server default `CURRENT_TIMESTAMP`).
   - Backfill existing rows: copy `current_maturity` into `desired_maturity`, copy NA flag, derive `progress_state` (`'complete'` if current exists or NA, else `'not_started'`).
   - Drop obsolete indexes if needed and recreate covering indexes on `(session_id, topic_id)` plus partial indexes for progress (if supported).
3. Update SQLAlchemy models (`app/infrastructure/models.py`) and dataclasses (`app/domain/models.py`) to match new fields and defaults.
4. Extend Pydantic schemas (`app/domain/schemas.py`, `app/web/schemas.py`) with dual-rating fields, evidence links (list[str]), and progress state enum validation.
5. Adjust repositories (`app/infrastructure/repositories_entry.py`) to upsert/read the new fields with validation (including desired ≥ current, NA coupling), updating tests in `tests/` for validation edge cases.
6. Revise seeds/fixtures (`scripts/seed_dataset.py`, test fixtures) to populate the new columns with sensible defaults (desired=current, empty evidence list, progress `'not_started'`).

## Phase 2 – Backend API Surface
1. Introduce new response schema `DimensionAssessmentResponse` encapsulating dimension metadata, rating scale, guidance (theme + topic), and flattened topic payloads with dual ratings.
2. Implement endpoint `GET /api/dimensions/{dimension_id}/assessment` in `app/web/routes/api.py`:
   - Gather dimension, theme, topic, explanations, theme-level guidance, and session-linked assessment entries in a single query pass.
   - Compute progress metrics (counts, percentage) for header.
   - Return evidence links parsed from JSON (empty list default) plus progress state.
3. Replace `record_topic_rating` flow with `record_topic_assessment` accepting dual ratings/service-layer validation housed in `app/application/api.py`.
4. Update POST endpoints (`/api/sessions/{session_id}/ratings` and `/ratings/single`) to accept payload `{ current_maturity, current_is_na, desired_maturity, desired_is_na, comment, evidence_links, progress_state }` and reuse service logic.
5. Ensure scoring utilities (`app/domain/services.py`, dashboard exports) read `current_maturity` (or `computed_score`) for averages; update analytics JSON builders accordingly.
6. Adjust exports/backups (`app/utils/backup.py`, `app/utils/resilience_radar.py`, etc.) to include new fields and remain backward compatible.
7. Refresh FastAPI response models/tests (`tests/test_dashboard_api.py`, `tests/test_scoring.py`, etc.) to target new schema names and enforce desired ≥ current.

## Phase 3 – Frontend Architecture
1. Remove `ThemesPage`, `TopicsPage`, and supporting hooks (`useThemes`, `useThemeTopics`) plus associated routes from `frontend/src/App.tsx`.
2. Create new component `frontend/src/components/DimensionAssessmentPage.tsx` based on `split_pane_resilience_assessment.jsx`:
   - Convert to TypeScript, integrate existing design system tokens/components, and wire to API types.
   - Implement left-rail search/filter, status pills (Current→Desired), and responsive behavior (top dropdown on mobile).
   - Add keyboard shortcut handling (useEffect cleanup, respect focused inputs).
   - Maintain “More” description toggle, stacked rating chips with constraint enforcement (Desired options filtered by Current), and comment/evidence sections.
   - Add evidence link editor (multi-line or chip field) persisting an array.
   - Show guidance panel with sticky behavior, highlighting selected level.
   - Surface header progress bar, Save/Next actions tied to active session; drop JSON export.
3. Build supporting hooks/types:
   - `useDimensionAssessment` to fetch `GET /api/dimensions/:id/assessment` (session-aware) and memoize derived structures.
   - Extend API types (`frontend/src/api/types.ts`) and client helpers to POST updated payloads.
   - Update `SessionContext`/`Header` to display dimension-specific progress when available.
4. Implement local state management mirroring server payload (dirty tracking, optimistic updates, validation prompts) leveraging existing navigation blocker for unsaved changes.
5. Add Save handler that batches modified topics and POSTs to `/api/sessions/:sessionId/ratings`, updating state on success; include inline error handling/toasts consistent with current UI.

## Phase 4 – Cleanup & Styling
1. Prune unused assets/styles:
   - Remove theme image references and related CSS blocks (`themes-grid`, etc.) from `frontend/src/index.css`.
   - Delete obsolete static images if no longer referenced.
   - Drop unused icons/constants tied to old pages.
2. Update routing/navigation copy (Breadcrumb context, header nav) to reflect new single assessment page.
3. Ensure mobile layout adjustments (top dropdown, collapsible guidance) are styled via existing Tailwind/CSS stack.

## Phase 5 – Verification & Documentation
1. Run Alembic migration and ensure downgrade path works for SQLite/MySQL (add tests if applicable).
2. Update unit/integration tests:
   - Backend: extend existing tests to cover dual rating invariants, new endpoint payload, migration backfill.
   - Frontend: adapt any Vitest/React Testing Library coverage (if present) or add smoke test for DimensionAssessmentPage.
3. Manual QA checklist:
   - Select dimension → new page renders; topics load with guidance.
   - Verify rating constraints, keyboard shortcuts, Save & Next flow, sticky guidance, progress bar updates.
   - Confirm evidence links persist and rehydrate.
   - Validate removal of old routes (direct navigation yields redirect/home).
4. Refresh docs (`README.md`, `new-ui-plan/steps.md` entry) with new workflow overview and migration instructions.

---

Dependencies & Sequencing:
- Phase 1 must complete before backend/frontend work that depends on new schema.
- Phase 2 relies on Phase 1 fields and should finish before frontend integration.
- Phase 3 consumes new API payloads; coordinate payload naming with backend to avoid churn.
- Phase 4 cleanup follows component replacement to avoid regressions.
- Phase 5 ensures overall stability before delivery.
