"""
Centralized configuration management for the resilience assessment application.

Provides environment-specific configuration with validation, type safety,
and comprehensive settings management using Pydantic.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

try:
    from pydantic import Field, field_validator, model_validator
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import (
        BaseSettings,
        Field,
        root_validator as model_validator,
        validator as field_validator,
    )
from functools import lru_cache


class DatabaseConfig(BaseSettings):
    """
    Database configuration settings.

    Handles both SQLite and MySQL configurations with validation
    and connection URL generation.

    Example:
        >>> # For SQLite
        >>> db_config = DatabaseConfig(backend="sqlite", sqlite_path="./test.db")
        >>> print(db_config.get_connection_url())
        >>> # sqlite:///./test.db

        >>> # For MySQL
        >>> db_config = DatabaseConfig(
        ...     backend="mysql",
        ...     mysql_host="localhost",
        ...     mysql_user="user",
        ...     mysql_password="pass",
        ...     mysql_database="resilience"
        ... )
        >>> print(db_config.get_connection_url())
        >>> # mysql+pymysql://user:pass@localhost:3306/resilience?charset=utf8mb4
    """

    backend: Literal["sqlite", "mysql"] = Field("sqlite", description="Database backend type")

    # SQLite settings
    sqlite_path: str | None = Field("./resilience.db", description="SQLite database file path")

    # MySQL settings
    mysql_host: str | None = Field("localhost", description="MySQL host")
    mysql_port: int | None = Field(3306, ge=1, le=65535, description="MySQL port")
    mysql_user: str | None = Field("root", description="MySQL username")
    mysql_password: str | None = Field("", description="MySQL password")
    mysql_database: str | None = Field("resilience", description="MySQL database name")
    mysql_charset: str = Field("utf8mb4", description="MySQL character set")

    # Connection settings
    pool_pre_ping: bool = Field(True, description="Enable connection pool pre-ping")
    pool_recycle: int = Field(3600, ge=60, description="Connection pool recycle time (seconds)")
    echo: bool = Field(False, description="Enable SQL query logging")

    model_config = {"env_prefix": "DB_", "case_sensitive": False}

    @field_validator("sqlite_path")
    def validate_sqlite_path(cls, v):
        """Validate SQLite path and ensure directory exists."""
        if v:
            path = Path(v)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Ensure .db extension
            if not path.suffix:
                v = str(path.with_suffix(".db"))
        return v

    @model_validator(mode="after")
    def validate_mysql_config(self):
        """Validate MySQL configuration completeness."""
        if self.backend == "mysql":
            missing = []
            if not self.mysql_host:
                missing.append("mysql_host")
            if not self.mysql_user:
                missing.append("mysql_user")
            if not self.mysql_database:
                missing.append("mysql_database")
            if missing:
                raise ValueError(f"MySQL backend requires: {', '.join(missing)}")
        return self

    def get_connection_url(self) -> str:
        """
        Generate database connection URL.

        Returns:
            Database connection URL string

        Raises:
            ValueError: If backend is unsupported or configuration is invalid
        """
        if self.backend == "sqlite":
            return f"sqlite:///{self.sqlite_path}"
        elif self.backend == "mysql":
            password_part = f":{self.mysql_password}" if self.mysql_password else ""
            return (
                f"mysql+pymysql://{self.mysql_user}{password_part}@{self.mysql_host}:"
                f"{self.mysql_port}/{self.mysql_database}?charset={self.mysql_charset}"
            )
        else:
            raise ValueError(f"Unsupported database backend: {self.backend}")

    def get_engine_options(self) -> dict[str, Any]:
        """
        Get SQLAlchemy engine options.

        Returns:
            Dictionary of engine configuration options
        """
        return {
            "echo": self.echo,
            "future": True,
            "pool_pre_ping": self.pool_pre_ping,
            "pool_recycle": self.pool_recycle,
        }


class LoggingConfig(BaseSettings):
    """
    Logging configuration settings.

    Manages logging levels, output formats, and file destinations
    with environment-specific defaults.

    Example:
        >>> log_config = LoggingConfig(level="DEBUG", file_path="./logs/app.log")
        >>> print(log_config.get_file_handler_config())
    """

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Minimum logging level"
    )
    file_path: str | None = Field("./logs/app.log", description="Log file path")
    max_bytes: int = Field(10 * 1024 * 1024, ge=1024, description="Max log file size in bytes")
    backup_count: int = Field(5, ge=1, description="Number of backup log files")
    structured: bool = Field(True, description="Use structured JSON logging")
    console_enabled: bool = Field(True, description="Enable console output")

    model_config = {"env_prefix": "LOG_", "case_sensitive": False}

    @field_validator("file_path")
    def validate_log_path(cls, v):
        """Ensure log directory exists."""
        if v:
            log_path = Path(v)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        return v

    def get_file_handler_config(self) -> dict[str, Any] | None:
        """Get file handler configuration if file logging is enabled."""
        if not self.file_path:
            return None

        return {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": self.file_path,
            "maxBytes": self.max_bytes,
            "backupCount": self.backup_count,
            "encoding": "utf-8",
        }


class SecurityConfig(BaseSettings):
    """
    Security configuration settings.

    Manages security-related settings like encryption keys,
    CORS settings, and input validation parameters.

    Example:
        >>> sec_config = SecurityConfig()
        >>> print(sec_config.max_input_length)
    """

    # Input validation
    max_input_length: int = Field(10000, ge=100, description="Maximum input string length")
    max_comment_length: int = Field(2000, ge=50, description="Maximum comment length")
    max_file_size_mb: int = Field(10, ge=1, le=100, description="Maximum upload file size (MB)")

    # Rate limiting
    rate_limit_requests: int = Field(100, ge=1, description="Rate limit requests per window")
    rate_limit_window_seconds: int = Field(60, ge=1, description="Rate limit window (seconds)")

    # Session security
    session_timeout_minutes: int = Field(480, ge=30, description="Session timeout (minutes)")

    # CORS settings (if needed for API)
    cors_origins: list[str] = Field(["*"], description="Allowed CORS origins")
    cors_methods: list[str] = Field(
        ["GET", "POST", "PUT", "DELETE"], description="Allowed CORS methods"
    )

    model_config = {"env_prefix": "SECURITY_", "case_sensitive": False}


class StreamlitConfig(BaseSettings):
    """
    Streamlit-specific configuration settings.

    Manages Streamlit app configuration, theming, and UI behavior.

    Example:
        >>> st_config = StreamlitConfig(theme="dark", page_title="Assessment App")
        >>> print(st_config.get_streamlit_config())
    """

    # App settings
    page_title: str = Field("Resilience Assessment", description="Page title")
    page_icon: str = Field("📊", description="Page icon")
    layout: Literal["centered", "wide"] = Field("wide", description="Page layout")
    initial_sidebar_state: Literal["auto", "expanded", "collapsed"] = Field(
        "expanded", description="Initial sidebar state"
    )

    # Theme settings
    theme: Literal["auto", "light", "dark"] = Field("auto", description="App theme")

    # Cache settings
    cache_ttl_seconds: int = Field(300, ge=60, description="Cache TTL in seconds")
    max_cached_entries: int = Field(100, ge=10, description="Maximum cached entries")

    # UI settings
    show_progress_bar: bool = Field(True, description="Show progress indicators")
    auto_refresh_seconds: int | None = Field(None, ge=30, description="Auto-refresh interval")

    model_config = {"env_prefix": "STREAMLIT_", "case_sensitive": False}

    def get_streamlit_config(self) -> dict[str, Any]:
        """Get configuration for Streamlit page config."""
        return {
            "page_title": self.page_title,
            "page_icon": self.page_icon,
            "layout": self.layout,
            "initial_sidebar_state": self.initial_sidebar_state,
        }


class ApplicationConfig(BaseSettings):
    """
    Main application configuration.

    Combines all configuration sections and provides a single
    point of access for application settings.

    Example:
        >>> config = get_settings()
        >>> print(config.app.environment)
        >>> db_url = config.database.get_connection_url()
    """

    # Environment
    environment: Literal["development", "testing", "production"] = Field(
        "development", description="Application environment"
    )
    debug: bool = Field(False, description="Enable debug mode")
    version: str = Field("0.1.0", description="Application version")

    # Feature flags
    enable_session_combining: bool = Field(True, description="Enable session combining feature")
    enable_data_export: bool = Field(True, description="Enable data export functionality")
    enable_backup_restore: bool = Field(False, description="Enable backup/restore functionality")

    # Performance settings
    query_timeout_seconds: int = Field(30, ge=5, description="Database query timeout")
    max_concurrent_sessions: int = Field(10, ge=1, description="Maximum concurrent sessions")

    # Data retention
    session_retention_days: int = Field(365, ge=30, description="Session retention period (days)")
    log_retention_days: int = Field(90, ge=7, description="Log retention period (days)")

    model_config = {"env_prefix": "APP_", "case_sensitive": False}

    @model_validator(mode="after")
    def debug_implies_development(self):
        """Ensure debug mode is only enabled in development."""
        if self.debug and self.environment == "production":
            raise ValueError("Debug mode cannot be enabled in production")
        return self


class Settings:
    """
    Complete application settings container.

    Provides structured access to all configuration sections
    with lazy loading and caching.

    Example:
        >>> settings = get_settings()
        >>> print(settings.database.get_connection_url())
        >>> print(settings.logging.level)
        >>> print(settings.app.environment)
    """

    def __init__(self):
        self._app: ApplicationConfig | None = None
        self._database: DatabaseConfig | None = None
        self._logging: LoggingConfig | None = None
        self._security: SecurityConfig | None = None
        self._streamlit: StreamlitConfig | None = None

    @property
    def app(self) -> ApplicationConfig:
        """Get application configuration."""
        if self._app is None:
            self._app = ApplicationConfig()
        return self._app

    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration."""
        if self._database is None:
            self._database = DatabaseConfig()
        return self._database

    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        if self._logging is None:
            # Set logging level based on environment
            level = "DEBUG" if self.app.debug else "INFO"
            if self.app.environment == "production":
                level = "WARNING"
            self._logging = LoggingConfig(level=level)
        return self._logging

    @property
    def security(self) -> SecurityConfig:
        """Get security configuration."""
        if self._security is None:
            self._security = SecurityConfig()
        return self._security

    @property
    def streamlit(self) -> StreamlitConfig:
        """Get Streamlit configuration."""
        if self._streamlit is None:
            self._streamlit = StreamlitConfig()
        return self._streamlit

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment == "production"

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app.environment == "testing"

    def get_environment_info(self) -> dict[str, Any]:
        """Get summary of current environment configuration."""
        return {
            "environment": self.app.environment,
            "version": self.app.version,
            "debug": self.app.debug,
            "database_backend": self.database.backend,
            "logging_level": self.logging.level,
            "features": {
                "session_combining": self.app.enable_session_combining,
                "data_export": self.app.enable_data_export,
                "backup_restore": self.app.enable_backup_restore,
            },
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get application settings instance (cached).

    This function uses LRU cache to ensure only one settings
    instance is created per application run.

    Returns:
        Settings instance with all configuration loaded

    Example:
        >>> settings = get_settings()
        >>> db_url = settings.database.get_connection_url()
        >>> log_level = settings.logging.level
    """
    return Settings()


def load_settings_from_file(file_path: str) -> Settings:
    """
    Load settings from a configuration file.

    Args:
        file_path: Path to configuration file (JSON, YAML, or TOML)

    Returns:
        Settings instance with loaded configuration

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If file format is unsupported or invalid

    Example:
        >>> settings = load_settings_from_file("config/production.json")
        >>> print(settings.app.environment)
    """
    import json
    from pathlib import Path

    config_path = Path(file_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    # Load configuration based on file extension
    if config_path.suffix.lower() == ".json":
        with open(config_path) as f:
            config_data = json.load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")

    # Set environment variables from config
    for section, values in config_data.items():
        if isinstance(values, dict):
            for key, value in values.items():
                env_key = f"{section.upper()}_{key.upper()}"
                os.environ[env_key] = str(value)

    # Clear cache and return new settings
    get_settings.cache_clear()
    return get_settings()


def override_settings(**kwargs) -> Settings:
    """
    Override specific settings for testing or development.

    Args:
        **kwargs: Settings to override (dot notation supported)

    Returns:
        Settings instance with overrides applied

    Example:
        >>> settings = override_settings(
        ...     app_environment="testing",
        ...     database_backend="sqlite",
        ...     database_sqlite_path=":memory:"
        ... )
    """
    # Set temporary environment variables
    for key, value in kwargs.items():
        env_key = key.upper().replace("_", "_", 1)  # Convert first underscore to section separator
        os.environ[env_key] = str(value)

    # Clear cache and return new settings
    get_settings.cache_clear()
    return get_settings()


def reset_settings() -> None:
    """Reset settings cache to reload from environment."""
    get_settings.cache_clear()


# Convenience function for backward compatibility
def get_database_config() -> DatabaseConfig:
    """Get database configuration (backward compatibility)."""
    return get_settings().database
