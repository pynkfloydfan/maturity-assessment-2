# Data Model Enhancements

## Dimension Table (`dimensions`)
- Add `description` (Text) populated from spreadsheet "Dimension Theme Topic Descrip" column `Dimension_Description`.
- Add `image_filename` (String, nullable) referencing packaged asset in `app/web/static/frontend/assets`.
- Add `image_alt` (String, nullable) for accessibility text.

## Theme Table (`themes`)
- Add `description` (Text) populated from `Theme_Description` column.
- Add `category` (String, nullable) populated from `Theme-Level-Generic`.`Category`.

## Topic Table (`topics`)
- Add `description` (Text) populated from `Topic_Description` column.

## Rating Scale (`rating_scale`)
- Add `description` (Text) using `CMMI-Level-Definitions`.`Definition` parsed by level.

## New Table: `theme_level_guidance`
- Purpose: store generic level descriptions per theme (Theme-Level-Generic sheet).
- Columns: `id` (PK), `theme_id` (FK themes.id, cascade delete), `level` (Integer, 1..5), `description` (Text), `created_at` timestamp default now.
- Unique constraint on (`theme_id`, `level`).

## Considerations
- Existing data to be migrated via Alembic by populating new nullable columns with default `None` and backfilling via seed script.
- Ensure Alembic migration is idempotent and handles existing rows by setting defaults to empty string or NULL.
- SQLAlchemy models to be updated accordingly with optional fields.
