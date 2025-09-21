"""
Custom exception classes for the resilience assessment application.

Provides structured error handling with user-friendly messages and proper
error categorization for different failure scenarios.
"""

from __future__ import annotations

from typing import Any


class ResilienceAssessmentError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        user_message: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.user_message = user_message or self._get_default_user_message()

    def _get_default_user_message(self) -> str:
        """Provide a user-friendly version of the error message."""
        return "An unexpected error occurred. Please try again."

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.message}"


class ValidationError(ResilienceAssessmentError):
    """Raised when input validation fails."""

    def __init__(
        self, field: str, message: str, value: Any = None, details: dict[str, Any] | None = None
    ):
        self.field = field
        self.value = value
        super().__init__(
            message=f"Validation failed for field '{field}': {message}",
            details=details or {"field": field, "value": value},
            user_message=f"Invalid {field.replace('_', ' ')}: {message}",
        )

    def _get_default_user_message(self) -> str:
        return f"Please check your input for {self.field.replace('_', ' ')} and try again."


class MultipleValidationError(ResilienceAssessmentError):
    """Raised when multiple validation errors occur."""

    def __init__(self, errors: list[ValidationError]):
        self.validation_errors = errors
        messages = [f"{e.field}: {e.message}" for e in errors]
        super().__init__(
            message=f"Multiple validation errors: {'; '.join(messages)}",
            details={
                "errors": [
                    {"field": e.field, "message": e.message, "value": e.value} for e in errors
                ]
            },
            user_message="Please correct the following errors and try again.",
        )

    def _get_default_user_message(self) -> str:
        return f"Please correct {len(self.validation_errors)} validation errors and try again."


class DatabaseError(ResilienceAssessmentError):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: str, details: dict[str, Any] | None = None):
        self.operation = operation
        super().__init__(
            message=f"Database error during {operation}: {message}",
            details=details or {"operation": operation},
            user_message="A database error occurred. Please try again in a moment.",
        )

    def _get_default_user_message(self) -> str:
        return "Unable to save your changes. Please try again."


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, operation="connection", details=details)

    def _get_default_user_message(self) -> str:
        return "Unable to connect to the database. Please check your connection and try again."


class IntegrityError(DatabaseError):
    """Raised when database integrity constraints are violated."""

    def __init__(
        self,
        message: str,
        constraint: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.constraint = constraint
        super().__init__(
            message=message,
            operation="integrity_check",
            details=details or {"constraint": constraint},
        )

    def _get_default_user_message(self) -> str:
        if self.constraint:
            if "unique" in self.constraint.lower():
                return "This item already exists. Please use a different name."
            elif "foreign" in self.constraint.lower():
                return "Referenced item no longer exists. Please refresh and try again."
        return "Data integrity error. Please check your input and try again."


class SessionError(ResilienceAssessmentError):
    """Raised when session operations fail."""

    def __init__(
        self,
        message: str,
        session_id: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.session_id = session_id
        super().__init__(
            message=message,
            details=details or {"session_id": session_id},
            user_message="Session error occurred. Please select a valid session and try again.",
        )


class SessionNotFoundError(SessionError):
    """Raised when a session is not found."""

    def __init__(self, session_id: int):
        super().__init__(message=f"Session with ID {session_id} not found", session_id=session_id)

    def _get_default_user_message(self) -> str:
        return "The selected session could not be found. Please select a different session."


class TopicError(ResilienceAssessmentError):
    """Raised when topic operations fail."""

    def __init__(
        self, message: str, topic_id: int | None = None, details: dict[str, Any] | None = None
    ):
        self.topic_id = topic_id
        super().__init__(
            message=message,
            details=details or {"topic_id": topic_id},
            user_message="Topic error occurred. Please try again.",
        )


class TopicNotFoundError(TopicError):
    """Raised when a topic is not found."""

    def __init__(self, topic_id: int):
        super().__init__(message=f"Topic with ID {topic_id} not found", topic_id=topic_id)

    def _get_default_user_message(self) -> str:
        return "The selected topic could not be found. Please refresh and try again."


class RatingError(ResilienceAssessmentError):
    """Raised when rating operations fail."""

    def __init__(
        self,
        message: str,
        rating_level: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.rating_level = rating_level
        super().__init__(
            message=message,
            details=details or {"rating_level": rating_level},
            user_message="Rating error occurred. Please check your rating and try again.",
        )


class InvalidRatingError(RatingError):
    """Raised when an invalid rating is provided."""

    def __init__(self, rating_level: Any):
        super().__init__(
            message=f"Invalid rating level: {rating_level}. Must be between 1-5 or N/A",
            rating_level=rating_level,
        )

    def _get_default_user_message(self) -> str:
        return "Please select a valid rating between 1-5 or mark as N/A."


class ConfigurationError(ResilienceAssessmentError):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.config_key = config_key
        super().__init__(
            message=message,
            details=details or {"config_key": config_key},
            user_message="Configuration error. Please check your settings.",
        )


class ExportError(ResilienceAssessmentError):
    """Raised when data export fails."""

    def __init__(
        self,
        message: str,
        export_format: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.export_format = export_format
        super().__init__(
            message=message,
            details=details or {"export_format": export_format},
            user_message="Export failed. Please try again or choose a different format.",
        )


class ImportError(ResilienceAssessmentError):
    """Raised when data import fails."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.file_path = file_path
        super().__init__(
            message=message,
            details=details or {"file_path": file_path},
            user_message="Import failed. Please check your file and try again.",
        )


class PermissionError(ResilienceAssessmentError):
    """Raised when user lacks required permissions."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.operation = operation
        super().__init__(
            message=message,
            details=details or {"operation": operation},
            user_message="You don't have permission to perform this operation.",
        )


class BusinessLogicError(ResilienceAssessmentError):
    """Raised when business logic constraints are violated."""

    def __init__(
        self, message: str, rule: str | None = None, details: dict[str, Any] | None = None
    ):
        self.rule = rule
        super().__init__(
            message=message,
            details=details or {"rule": rule},
            user_message="This operation cannot be completed due to business rules.",
        )


def handle_database_error(e: Exception, operation: str = "database operation") -> DatabaseError:
    """
    Convert generic database exceptions to appropriate custom exceptions.

    Args:
        e: The original exception
        operation: Description of the operation that failed

    Returns:
        Appropriate DatabaseError subclass

    Example:
        >>> try:
        ...     session.commit()
        >>> except Exception as e:
        ...     raise handle_database_error(e, "commit transaction")
    """
    error_msg = str(e).lower()

    if "connection" in error_msg or "timeout" in error_msg:
        return ConnectionError(str(e))
    elif "unique constraint" in error_msg or "duplicate" in error_msg:
        return IntegrityError(str(e), constraint="unique")
    elif "foreign key" in error_msg or "foreign_key" in error_msg:
        return IntegrityError(str(e), constraint="foreign_key")
    elif "check constraint" in error_msg:
        return IntegrityError(str(e), constraint="check")
    else:
        return DatabaseError(str(e), operation)


def create_user_friendly_error_message(error: Exception) -> str:
    """
    Create a user-friendly error message from any exception.

    Args:
        error: The exception to convert

    Returns:
        User-friendly error message

    Example:
        >>> error = ValidationError("name", "cannot be empty")
        >>> message = create_user_friendly_error_message(error)
        >>> print(message)  # "Invalid name: cannot be empty"
    """
    if isinstance(error, ResilienceAssessmentError):
        return error.user_message

    # Generic error handling for unexpected exceptions
    error_type = type(error).__name__
    messages = {
        "ValueError": "Invalid input provided. Please check your data and try again.",
        "KeyError": "Required information is missing. Please check your input.",
        "TypeError": "Incorrect data type provided. Please check your input format.",
    }
    return messages.get(
        error_type, "An unexpected error occurred. Please try again or contact support."
    )


def log_error_details(error: Exception, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Create structured error details for logging.

    Args:
        error: The exception to log
        context: Additional context information

    Returns:
        Dictionary with structured error details

    Example:
        >>> error = DatabaseError("Connection failed", "connect")
        >>> details = log_error_details(error, {"user_id": 123})
        >>> print(details["error_type"])  # "DatabaseError"
    """
    details = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
    }

    if isinstance(error, ResilienceAssessmentError):
        details.update({"user_message": error.user_message, "error_details": error.details})

    return details
