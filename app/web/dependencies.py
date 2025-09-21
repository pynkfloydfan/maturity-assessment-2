from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.config import DatabaseConfig, get_settings
from app.infrastructure.db import create_database_engine, create_session_factory


def get_db_config(request: Request) -> DatabaseConfig:
    config = getattr(request.app.state, "db_config", None)
    if config is None:
        config = get_settings().database
        request.app.state.db_config = config
    return config


def _config_to_dict(config: DatabaseConfig) -> dict[str, object]:
    if hasattr(config, "model_dump"):
        return config.model_dump()  # type: ignore[no-any-return]
    return config.dict()  # type: ignore[no-any-return]


def get_session_factory(request: Request) -> sessionmaker[Session]:
    config = get_db_config(request)
    cached_factory = getattr(request.app.state, "session_factory", None)
    cached_config = getattr(request.app.state, "session_factory_config", None)

    current_config_dict = _config_to_dict(config)

    if cached_factory is not None and cached_config == current_config_dict:
        return cached_factory

    engine = create_database_engine(config)
    session_factory = create_session_factory(engine)

    request.app.state.session_factory = session_factory
    request.app.state.session_factory_config = current_config_dict

    return session_factory


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = get_session_factory(request)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()

