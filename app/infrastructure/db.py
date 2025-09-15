"""
Database connection and session management with centralized configuration.

This module provides database connectivity using the centralized configuration
system, with proper error handling and logging integration.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .config import DatabaseConfig, get_settings
from .logging import get_logger

logger = get_logger(__name__)


def create_database_engine(config: DatabaseConfig = None) -> Engine:
    """
    Create SQLAlchemy engine with proper configuration.

    Args:
        config: Database configuration (uses default if None)

    Returns:
        Configured SQLAlchemy engine

    Example:
        >>> engine = create_database_engine()
        >>> # Uses configuration from environment/settings
    """
    if config is None:
        config = get_settings().database

    connection_url = config.get_connection_url()
    engine_options = config.get_engine_options()

    logger.info(f"Creating database engine for {config.backend} backend")
    logger.debug(f"Connection URL: {connection_url.split('@')[0]}@***")  # Hide credentials in logs

    try:
        engine = create_engine(connection_url, **engine_options)
        logger.info("Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {str(e)}")
        raise


def create_session_factory(engine: Engine = None) -> sessionmaker:
    """
    Create SQLAlchemy session factory.

    Args:
        engine: Database engine (creates new one if None)

    Returns:
        Configured sessionmaker factory

    Example:
        >>> SessionLocal = create_session_factory()
        >>> with SessionLocal() as session:
        ...     # Use session for database operations
        ...     pass
    """
    if engine is None:
        engine = create_database_engine()

    logger.info("Creating session factory")

    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
    )

    logger.info("Session factory created successfully")
    return SessionLocal


def make_engine_and_session(connection_url: str = None) -> tuple[Engine, sessionmaker]:
    """
    Create engine and session factory (backward compatibility).

    Args:
        connection_url: Database URL (uses config if None)

    Returns:
        Tuple of (engine, session_factory)

    Example:
        >>> engine, SessionLocal = make_engine_and_session()
        >>> with SessionLocal() as session:
        ...     # Database operations
        ...     pass
    """
    if connection_url:
        # Legacy mode: create engine from URL
        logger.info("Using legacy connection URL mode")
        engine = create_engine(connection_url, echo=False, future=True, pool_pre_ping=True)
        SessionLocal = sessionmaker(
            bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
        )
    else:
        # New mode: use configuration
        engine = create_database_engine()
        SessionLocal = create_session_factory(engine)

    return engine, SessionLocal


def get_database_url() -> str:
    """
    Get database connection URL from configuration.

    Returns:
        Database connection URL

    Example:
        >>> url = get_database_url()
        >>> print(url)  # sqlite:///./resilience.db
    """
    return get_settings().database.get_connection_url()


def is_database_configured() -> bool:
    """
    Check if database is properly configured.

    Returns:
        True if database configuration is valid

    Example:
        >>> if is_database_configured():
        ...     engine = create_database_engine()
    """
    try:
        config = get_settings().database
        config.get_connection_url()
        return True
    except Exception as e:
        logger.warning(f"Database configuration invalid: {str(e)}")
        return False
