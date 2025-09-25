from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.infrastructure.config import DatabaseConfig
from app.infrastructure.db import make_engine_and_session
from app.infrastructure.models import (
    Base,
    DimensionORM,
    ExplanationORM,
    RatingScaleORM,
    ThemeLevelGuidanceORM,
    ThemeORM,
    TopicORM,
)

RatingColumn = Tuple[int, str, str]


DIMENSION_IMAGE_MAP: dict[str, str] = {
    "Governance & Leadership": "governance-leadership.png",
    "Risk Assessment & Management": "risk-assessment-management.png",
    "BC & DR Planning": "bc-dr-planning.png",
    "Process & Dependency Mapping": "process-dependency-mapping.png",
    "IT & Cyber Resilience": "it-cyber-resilience.png",
    "Crisis Comms & Incident Mgmt": "crisis-comms-incident-mgmt.png",
    "Third-Party Resilience": "third-party-resilience.png",
    "Culture & Human Factors": "culture-human-factors.png",
    "Regulatory Compliance & Resolvability": "regulatory-compliance-resolvability.png",
}


def clean_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_optional(value: object) -> str | None:
    text = clean_text(value)
    return text or None


def detect_rating_columns(columns: Iterable[str]) -> list[RatingColumn]:
    pattern = re.compile(r"^(\d)\s+(.+)$")
    result: list[RatingColumn] = []
    for col in columns:
        match = pattern.match(col.strip())
        if match:
            level = int(match.group(1))
            label = match.group(2).strip()
            result.append((level, label, col))
    result.sort(key=lambda item: item[0])
    return result


def split_bullets(cell: object) -> list[str]:
    if not isinstance(cell, str):
        return []
    parts = re.split(r"[\n\r]+|\u2022", cell)
    cleaned = [p.strip(" \t-•") for p in parts if p and p.strip(" \t-•")]
    return cleaned


def load_cmmi_definitions(excel_path: Path) -> dict[int, dict[str, str | None]]:
    df = pd.read_excel(excel_path, sheet_name="CMMI-Level-Definitions")
    mapping: dict[int, dict[str, str | None]] = {}
    pattern = re.compile(r"^(\d)\s*(.+)$")
    for _, row in df.iterrows():
        raw_level = clean_text(row.get("Level"))
        if not raw_level:
            continue
        match = pattern.match(raw_level)
        if not match:
            continue
        level = int(match.group(1))
        label = match.group(2).strip()
        mapping[level] = {
            "label": label,
            "description": clean_optional(row.get("Definition")),
        }
    return mapping


def load_descriptive_metadata(
    excel_path: Path,
) -> tuple[dict[str, str | None], dict[tuple[str, str], str | None], dict[tuple[str, str, str], str | None]]:
    df = pd.read_excel(excel_path, sheet_name="Dimension Theme Topic Descrip")
    dimensions: dict[str, str | None] = {}
    themes: dict[tuple[str, str], str | None] = {}
    topics: dict[tuple[str, str, str], str | None] = {}

    for _, row in df.iterrows():
        dimension = clean_text(row.get("Dimension"))
        theme = clean_text(row.get("Theme"))
        topic = clean_text(row.get("Topic"))

        if dimension and dimension not in dimensions:
            dimensions[dimension] = clean_optional(row.get("Dimension_Description"))
        if dimension and theme and (dimension, theme) not in themes:
            themes[(dimension, theme)] = clean_optional(row.get("Theme_Description"))
        if dimension and theme and topic:
            topics[(dimension, theme, topic)] = clean_optional(row.get("Topic_Description"))

    return dimensions, themes, topics


def load_theme_generics(
    excel_path: Path,
) -> tuple[dict[str, str | None], dict[str, dict[int, str]]]:
    df = pd.read_excel(excel_path, sheet_name="Theme-Level-Generic")
    categories: dict[str, str | None] = {}
    levels: dict[str, dict[int, str]] = {}
    for _, row in df.iterrows():
        theme = clean_text(row.get("Theme"))
        if not theme:
            continue
        categories[theme] = clean_optional(row.get("Category"))
        level_map: dict[int, str] = {}
        for level in range(1, 6):
            column = f"L{level} Generic"
            text = clean_text(row.get(column))
            if text:
                level_map[level] = text
        levels[theme] = level_map
    return categories, levels


def sync_rating_scale(s: Session, rating_cols: list[RatingColumn], cmmi: dict[int, dict[str, str | None]]) -> None:
    for level, fallback_label, _ in rating_cols:
        info = cmmi.get(level)
        label = info.get("label") if info else fallback_label
        description = info.get("description") if info else None
        existing = s.get(RatingScaleORM, level)
        if existing is None:
            s.add(RatingScaleORM(level=level, label=label, description=description))
        else:
            existing.label = label
            existing.description = description


def sync_theme_guidance(
    s: Session, theme: ThemeORM, guidance_levels: dict[int, str]
) -> None:
    existing = {
        gl.level: gl
        for gl in s.query(ThemeLevelGuidanceORM).filter(ThemeLevelGuidanceORM.theme_id == theme.id).all()
    }
    for level, description in guidance_levels.items():
        entry = existing.get(level)
        if entry:
            entry.description = description
        else:
            s.add(ThemeLevelGuidanceORM(theme_id=theme.id, level=level, description=description))
    # Remove stale levels not present anymore
    stale_levels = set(existing) - set(guidance_levels)
    if stale_levels:
        s.execute(
            delete(ThemeLevelGuidanceORM).where(
                ThemeLevelGuidanceORM.theme_id == theme.id,
                ThemeLevelGuidanceORM.level.in_(list(stale_levels)),
            )
        )


def seed_from_excel(s: Session, excel_path: Path) -> None:
    framework_df = pd.read_excel(excel_path, sheet_name="Enhanced Framework")
    required = {"Dimension", "Theme", "Topic"}
    missing = required - set(framework_df.columns)
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    cmmi_defs = load_cmmi_definitions(excel_path)
    dim_descriptions, theme_descriptions, topic_descriptions = load_descriptive_metadata(excel_path)
    theme_categories, theme_generic_levels = load_theme_generics(excel_path)

    rating_cols = detect_rating_columns(list(framework_df.columns))
    sync_rating_scale(s, rating_cols, cmmi_defs)

    dim_cache: dict[str, int] = {}
    theme_cache: dict[tuple[int, str], int] = {}
    processed_topics: set[int] = set()
    processed_themes: set[int] = set()

    for _, row in framework_df.iterrows():
        dimension_name = clean_text(row["Dimension"])
        theme_name = clean_text(row["Theme"])
        topic_name = clean_text(row["Topic"])

        if not (dimension_name and theme_name and topic_name):
            continue

        dim_id = dim_cache.get(dimension_name)
        if dim_id is None:
            dimension = s.query(DimensionORM).filter_by(name=dimension_name).one_or_none()
            if dimension is None:
                dimension = DimensionORM(name=dimension_name)
                s.add(dimension)
                s.flush()
            dimension.description = dim_descriptions.get(dimension_name)
            if dimension.image_filename is None:
                dimension.image_filename = DIMENSION_IMAGE_MAP.get(dimension_name)
            if dimension.image_alt is None:
                dimension.image_alt = dimension_name or None
            dim_cache[dimension_name] = dimension.id
            dim_id = dimension.id
        else:
            dimension = s.get(DimensionORM, dim_id)
            if dimension and dimension.description is None:
                dimension.description = dim_descriptions.get(dimension_name)
            if dimension and dimension.image_filename is None:
                dimension.image_filename = DIMENSION_IMAGE_MAP.get(dimension_name)
            if dimension and dimension.image_alt is None:
                dimension.image_alt = dimension_name or None

        theme_key = (dim_id, theme_name)
        theme_id = theme_cache.get(theme_key)
        if theme_id is None:
            theme = (
                s.query(ThemeORM)
                .filter_by(dimension_id=dim_id, name=theme_name)
                .one_or_none()
            )
            if theme is None:
                theme = ThemeORM(dimension_id=dim_id, name=theme_name)
                s.add(theme)
                s.flush()
            theme.description = theme_descriptions.get((dimension_name, theme_name))
            theme.category = theme_categories.get(theme_name)
            theme_cache[theme_key] = theme.id
            theme_id = theme.id
        else:
            theme = s.get(ThemeORM, theme_id)
            if theme:
                if theme.description is None:
                    theme.description = theme_descriptions.get((dimension_name, theme_name))
                if theme.category is None:
                    theme.category = theme_categories.get(theme_name)

        if theme and theme.id not in processed_themes:
            levels = theme_generic_levels.get(theme_name, {})
            if levels:
                sync_theme_guidance(s, theme, levels)
            processed_themes.add(theme.id)

        topic = (
            s.query(TopicORM)
            .filter_by(theme_id=theme_id, name=topic_name)
            .one_or_none()
        )
        if topic is None:
            topic = TopicORM(theme_id=theme_id, name=topic_name)
            s.add(topic)
            s.flush()
        topic.description = topic_descriptions.get((dimension_name, theme_name, topic_name))

        if topic.id not in processed_topics:
            s.execute(delete(ExplanationORM).where(ExplanationORM.topic_id == topic.id))
            processed_topics.add(topic.id)

        for level, _label, column in rating_cols:
            bullets = split_bullets(row.get(column))
            for bullet in bullets:
                s.add(ExplanationORM(topic_id=topic.id, level=level, text=bullet))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed DB from Enhanced Operational Resilience Maturity workbook"
    )

    backend_default = os.environ.get("DB_BACKEND", "sqlite")
    sqlite_default = os.environ.get("DB_SQLITE_PATH") or os.environ.get("SQLITE_PATH", "./resilience.db")
    mysql_host_default = os.environ.get("DB_MYSQL_HOST") or os.environ.get("MYSQL_HOST", "localhost")
    mysql_port_default = int(
        os.environ.get("DB_MYSQL_PORT")
        or os.environ.get("MYSQL_PORT")
        or 3306
    )
    mysql_user_default = os.environ.get("DB_MYSQL_USER") or os.environ.get("MYSQL_USER", "root")
    mysql_password_default = os.environ.get("DB_MYSQL_PASSWORD") or os.environ.get("MYSQL_PASSWORD", "")
    mysql_database_default = os.environ.get("DB_MYSQL_DATABASE") or os.environ.get("MYSQL_DB", "resilience")

    parser.add_argument(
        "--backend", choices=["sqlite", "mysql"], default=backend_default
    )
    parser.add_argument("--sqlite-path", default=sqlite_default)
    parser.add_argument("--mysql-host", default=mysql_host_default)
    parser.add_argument("--mysql-port", type=int, default=mysql_port_default)
    parser.add_argument("--mysql-user", default=mysql_user_default)
    parser.add_argument("--mysql-password", default=mysql_password_default)
    parser.add_argument("--mysql-database", "--mysql-db", dest="mysql_database", default=mysql_database_default)
    parser.add_argument(
        "--excel-path",
        default="app/source_data/enhanced_operational_resilience_maturity_v6.xlsx",
    )
    args = parser.parse_args()

    cfg = DatabaseConfig(
        backend=args.backend,
        sqlite_path=args.sqlite_path,
        mysql_host=args.mysql_host,
        mysql_port=args.mysql_port,
        mysql_user=args.mysql_user,
        mysql_password=args.mysql_password,
        mysql_database=args.mysql_database,
    )
    url = cfg.get_connection_url()
    engine, SessionLocal = make_engine_and_session(url)

    Base.metadata.create_all(engine)

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        print(f"ERROR: Excel file not found at {excel_path}", file=sys.stderr)
        sys.exit(1)

    with SessionLocal() as session:
        seed_from_excel(session, excel_path)
        session.commit()
    print("Seed completed.")


if __name__ == "__main__":
    main()

