"""
Centralized logging configuration for the resilience assessment application.

Provides structured logging with appropriate levels, formatting, and
context tracking for debugging and monitoring.
"""

import json
import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra context if available
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation

        # Include exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """Filter that adds request context to log records."""

    def __init__(self):
        super().__init__()
        self.context = {}

    def set_context(self, **kwargs):
        """Set context variables for logging."""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear all context variables."""
        self.context.clear()

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


# Global context filter instance
context_filter = ContextFilter()


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    structured: bool = True,
    enable_console: bool = True,
) -> None:
    """
    Set up centralized logging configuration.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        structured: Whether to use structured JSON formatting
        enable_console: Whether to enable console output

    Example:
        >>> setup_logging(level="DEBUG", log_file="./logs/app.log")
    """
    # Create logs directory if file logging is enabled
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "filters": {"context": {"()": lambda: context_filter}},
        "handlers": {},
        "loggers": {
            "app": {"level": level, "handlers": [], "propagate": False},
            "sqlalchemy.engine": {
                "level": "WARNING",  # Reduce SQLAlchemy noise
                "handlers": [],
                "propagate": False,
            },
            "streamlit": {
                "level": "WARNING",  # Reduce Streamlit noise
                "handlers": [],
                "propagate": False,
            },
        },
        "root": {"level": level, "handlers": []},
    }

    handlers = []

    # Console handler
    if enable_console:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": level,
            "formatter": "structured" if structured else "standard",
            "filters": ["context"],
            "stream": "ext://sys.stdout",
        }
        handlers.append("console")

    # File handler
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": level,
            "formatter": "structured",
            "filters": ["context"],
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }
        handlers.append("file")

    # Apply handlers to all loggers
    for logger_name in ["app", "sqlalchemy.engine", "streamlit", "root"]:
        if logger_name in config["loggers"]:
            config["loggers"][logger_name]["handlers"] = handlers
        else:
            config[logger_name]["handlers"] = handlers

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    full = name if name.startswith("app.") or name == "app" else f"app.{name}"
    return logging.getLogger(full)


def set_context(**kwargs) -> None:
    """
    Set logging context variables.

    Args:
        **kwargs: Context variables to set

    Example:
        >>> set_context(user_id=123, session_id=456)
    """
    context_filter.set_context(**kwargs)


def clear_context() -> None:
    """Clear all logging context variables."""
    context_filter.clear_context()


class LogContext:
    """Context manager for temporary logging context."""

    def __init__(self, **kwargs):
        self.context = kwargs
        self.previous_context = {}

    def __enter__(self):
        # Save current context
        self.previous_context = context_filter.context.copy()
        # Set new context
        context_filter.set_context(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        context_filter.context = self.previous_context


def log_operation(operation: str, logger: logging.Logger | None = None):
    """
    Decorator for logging function operations.

    Args:
        operation: Description of the operation
        logger: Optional logger instance (defaults to function's module logger)

    Example:
        >>> @log_operation("create_session")
        ... def create_session(name: str):
        ...     pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            func_logger = logger or get_logger(func.__module__)

            with LogContext(operation=operation):
                func_logger.info(f"Starting {operation}")
                try:
                    result = func(*args, **kwargs)
                    func_logger.info(f"Completed {operation} successfully")
                    return result
                except Exception as e:
                    func_logger.error(f"Failed {operation}: {str(e)}", exc_info=True)
                    raise

        return wrapper

    return decorator


def log_database_operation(operation: str):
    """
    Decorator for logging database operations with additional context.

    Args:
        operation: Description of the database operation

    Example:
        >>> @log_database_operation("insert_session")
        ... def create_session_record(session_data):
        ...     pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger("database")

            with LogContext(operation=f"db_{operation}"):
                # set to log at INFO level for db operations
                logger.info(f"Starting database operation: {operation}")
                start_time = datetime.utcnow()

                try:
                    result = func(*args, **kwargs)
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.info(f"Database operation {operation} completed in {duration:.3f}s")
                    return result
                except Exception as e:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.error(
                        f"Database operation {operation} failed after {duration:.3f}s: {str(e)}",
                        exc_info=True,
                    )
                    raise

        return wrapper

    return decorator


def configure_development_logging():
    """Configure logging for development environment."""
    setup_logging(
        level="DEBUG", log_file="./logs/development.log", structured=False, enable_console=True
    )


def configure_production_logging():
    """Configure logging for production environment."""
    setup_logging(
        level="INFO", log_file="./logs/production.log", structured=True, enable_console=False
    )


def configure_test_logging():
    """Configure logging for testing environment."""
    setup_logging(level="WARNING", log_file=None, structured=False, enable_console=False)


# Auto-configure based on environment
def auto_configure_logging():
    """Automatically configure logging based on environment variables."""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        configure_production_logging()
    elif env == "test":
        configure_test_logging()
    else:
        configure_development_logging()

    logger = get_logger(__name__)
    logger.info(f"Logging configured for {env} environment")


# Initialize logging when module is imported
if not logging.getLogger().handlers:
    auto_configure_logging()
