from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.infrastructure.config import DatabaseConfig as DBConfig
from app.infrastructure.models import Base


def initialise_database(engine: Engine) -> bool:
    """
    Ensure all ORM tables exist.

    Returns:
        True if every table already existed before this call, False if at least one table
        needed to be created.
    """

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = [table.name for table in Base.metadata.sorted_tables]
    already_exists = all(table in existing_tables for table in expected_tables)
    Base.metadata.create_all(engine)
    return already_exists


def seed_database_from_excel(cfg: DBConfig, excel_path: Path) -> tuple[int, str, str, str]:
    cmd = [sys.executable, "scripts/seed_dataset.py", "--backend", cfg.backend]
    if cfg.backend == "sqlite":
        cmd += ["--sqlite-path", cfg.sqlite_path or "./resilience.db"]
    else:
        cmd += [
            "--mysql-host",
            cfg.mysql_host or "localhost",
            "--mysql-port",
            str(cfg.mysql_port or 3306),
            "--mysql-user",
            cfg.mysql_user or "root",
            "--mysql-password",
            cfg.mysql_password or "",
            "--mysql-database",
            cfg.mysql_database or "resilience",
        ]
    cmd += ["--excel-path", str(excel_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, " ".join(cmd), res.stdout, res.stderr
