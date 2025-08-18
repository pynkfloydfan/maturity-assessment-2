from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@dataclass
class DBConfig:
    backend: str  # 'sqlite' or 'mysql'
    sqlite_path: Optional[str] = None
    mysql_host: Optional[str] = None
    mysql_port: Optional[int] = None
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_db: Optional[str] = None

def build_connection_url(cfg: DBConfig) -> str:
    if cfg.backend == "sqlite":
        path = cfg.sqlite_path or "./resilience.db"
        return f"sqlite:///{path}"
    elif cfg.backend == "mysql":
        host = cfg.mysql_host or "localhost"
        port = cfg.mysql_port or 3306
        user = cfg.mysql_user or "root"
        pw = cfg.mysql_password or ""
        db = cfg.mysql_db or "resilience"
        # MySQL 5.6: use utf8 (or utf8mb4 if instance supports)
        return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}?charset=utf8mb4"
    else:
        raise ValueError("Unsupported backend. Use 'sqlite' or 'mysql'.")

def make_engine_and_session(url: str):
    engine = create_engine(url, echo=False, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(
        bind=engine, 
        autoflush=False, 
        autocommit=False, 
        expire_on_commit=False, 
        future=True
    )
    return engine, SessionLocal
