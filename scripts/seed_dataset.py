from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.infrastructure.db import DBConfig, build_connection_url, make_engine_and_session
from app.infrastructure.models import (
    Base,
    DimensionORM,
    ExplanationORM,
    RatingScaleORM,
    ThemeORM,
    TopicORM,
)


def detect_rating_columns(columns: list[str]) -> list[tuple[int, str, str]]:
    # Returns tuples of (level, label, column_name)
    pattern = re.compile(r"^(\d)\s+(.+)$")
    result = []
    for col in columns:
        m = pattern.match(col.strip())
        if m:
            level = int(m.group(1))
            label = m.group(2).strip()
            result.append((level, label, col))
    result.sort(key=lambda x: x[0])
    return result


def split_bullets(cell: str) -> list[str]:
    if not isinstance(cell, str):
        return []
    # split on • and newlines
    parts = re.split(r"[\n\r]+|\u2022", cell)
    cleaned = [p.strip(" •\t-") for p in parts if p and p.strip(" •\t-")]
    return cleaned


def seed_from_excel(s: Session, excel_path: Path):
    df = pd.read_excel(excel_path, sheet_name="Enhanced Framework")
    # enforce required columns
    required = {"Dimension", "Theme", "Topic"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    # upsert rating scale
    rating_cols = detect_rating_columns(list(df.columns))
    for level, label, _ in rating_cols:
        obj = s.get(RatingScaleORM, level)
        if obj is None:
            s.add(RatingScaleORM(level=level, label=label))
        else:
            obj.label = label

    # build caches to avoid extra queries
    dim_cache: dict[str, int] = {}
    theme_cache: dict[tuple[int, str], int] = {}

    for _, row in df.iterrows():
        dname = str(row["Dimension"]).strip()
        tname = str(row["Theme"]).strip()
        qname = str(row["Topic"]).strip()

        dim_id = dim_cache.get(dname)
        if dim_id is None:
            dim = s.query(DimensionORM).filter_by(name=dname).one_or_none()
            if dim is None:
                dim = DimensionORM(name=dname)
                s.add(dim)
                s.flush()
            dim_id = dim.id
            dim_cache[dname] = dim_id

        theme_key = (dim_id, tname)
        theme_id = theme_cache.get(theme_key)
        if theme_id is None:
            theme = s.query(ThemeORM).filter_by(dimension_id=dim_id, name=tname).one_or_none()
            if theme is None:
                theme = ThemeORM(dimension_id=dim_id, name=tname)
                s.add(theme)
                s.flush()
            theme_id = theme.id
            theme_cache[theme_key] = theme_id

        topic = s.query(TopicORM).filter_by(theme_id=theme_id, name=qname).one_or_none()
        if topic is None:
            topic = TopicORM(theme_id=theme_id, name=qname)
            s.add(topic)
            s.flush()

        # explanations
        for level, _label, col in rating_cols:
            bullets = split_bullets(row[col])
            for b in bullets:
                s.add(ExplanationORM(topic_id=topic.id, level=level, text=b))


def main():
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(
        description="Seed DB from enhanced-operational-resilience-maturity-assessment.xlsx"
    )
    parser.add_argument(
        "--backend", choices=["sqlite", "mysql"], default=os.environ.get("DB_BACKEND", "sqlite")
    )
    parser.add_argument("--sqlite-path", default=os.environ.get("SQLITE_PATH", "./resilience.db"))
    parser.add_argument("--mysql-host", default=os.environ.get("MYSQL_HOST", "localhost"))
    parser.add_argument("--mysql-port", type=int, default=int(os.environ.get("MYSQL_PORT", 3306)))
    parser.add_argument("--mysql-user", default=os.environ.get("MYSQL_USER", "root"))
    parser.add_argument("--mysql-password", default=os.environ.get("MYSQL_PASSWORD", ""))
    parser.add_argument("--mysql-db", default=os.environ.get("MYSQL_DB", "resilience"))
    parser.add_argument(
        "--excel-path", default="enhanced-operational-resilience-maturity-assessment.xlsx"
    )
    args = parser.parse_args()

    cfg = DBConfig(
        backend=args.backend,
        sqlite_path=args.sqlite_path,
        mysql_host=args.mysql_host,
        mysql_port=args.mysql_port,
        mysql_user=args.mysql_user,
        mysql_password=args.mysql_password,
        mysql_db=args.mysql_db,
    )
    url = build_connection_url(cfg)
    engine, SessionLocal = make_engine_and_session(url)
    # Create tables if not existing (alembic recommended for production)

    Base.metadata.create_all(engine)

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        print(f"ERROR: Excel file not found at {excel_path}", file=sys.stderr)
        sys.exit(1)

    with SessionLocal() as s:
        seed_from_excel(s, excel_path)
        s.commit()
    print("Seed completed.")


if __name__ == "__main__":
    main()
