from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import Engine

from app.infrastructure.config import DatabaseConfig as DBConfig
from app.infrastructure.models import Base


def initialise_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)


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
            "--mysql-db",
            cfg.mysql_db or "resilience",
        ]
    cmd += ["--excel-path", str(excel_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, " ".join(cmd), res.stdout, res.stderr

