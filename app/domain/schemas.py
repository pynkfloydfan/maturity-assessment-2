"""
Pydantic schemas for comprehensive input validation across the application.

These schemas provide robust validation for all user inputs, API requests,
and data transfers within the resilience assessment system.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from html import unescape
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class BaseValidationSchema(BaseModel):
    """Base schema with common validation utilities."""

    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        use_enum_values = True

    @field_validator("*", mode="before")
    def sanitize_strings(cls, v):
        """Sanitize string inputs to prevent XSS and injection attacks."""
        if isinstance(v, str):
            # Normalize whitespace and decode any HTML entities to preserve user intent
            cleaned = unescape(v.strip())
            # Strip script tags entirely
            cleaned = re.sub(
                r"<\s*script[^>]*>.*?<\s*/\s*script\s*>",
                "",
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
            # Remove any remaining inline HTML tags
            cleaned = re.sub(r"<[^>]+>", "", cleaned)
            # Remove null bytes and control characters
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", cleaned)
            return cleaned
        return v


class CMMILevel(BaseModel):
    """Validation for CMMI maturity levels."""

    level: int = Field(..., ge=1, le=5, description="CMMI level between 1-5")

    @field_validator("level")
    def validate_cmmi_level(cls, v):
        """Ensure CMMI level is valid."""
        if v not in [1, 2, 3, 4, 5]:
            raise ValueError("CMMI level must be between 1 and 5 inclusive")
        return v



class SessionCreationInput(BaseValidationSchema):
    """Validation schema for creating assessment sessions."""

    name: str = Field(..., min_length=1, max_length=255, description="Session name")
    assessor: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=10000)
    created_at: datetime | None = None

    @field_validator("name")
    def validate_session_name(cls, v):
        """Validate session name format."""
        if not v or not v.strip():
            raise ValueError("Session name cannot be empty")

        # Check for potentially problematic characters
        if re.search(r'[<>"\'/\\]', v):
            raise ValueError("Session name contains invalid characters")

        return v.strip()

    @field_validator("assessor")
    def validate_optional_fields(cls, v):
        """Validate optional string fields."""
        if v is not None and len(v.strip()) == 0:
            return None
        return v


ProgressState = Literal["not_started", "in_progress", "complete"]


class AssessmentEntryInput(BaseValidationSchema):
    """Validation schema for assessment entries with dual maturity ratings."""

    session_id: int = Field(..., gt=0)
    topic_id: int = Field(..., gt=0)
    current_maturity: int | None = Field(None, ge=1, le=5)
    desired_maturity: int | None = Field(None, ge=1, le=5)
    computed_score: Decimal | None = Field(None, ge=0, le=5, decimal_places=2)
    current_is_na: bool = Field(default=False)
    desired_is_na: bool = Field(default=False)
    comment: str | None = Field(None, max_length=2000)
    evidence_links: list[str] | None = Field(default=None)
    progress_state: ProgressState = Field(default="not_started")

    @model_validator(mode="after")
    def validate_entry_consistency(self):
        """Ensure entry data is consistent with business rules."""
        if self.current_is_na:
            if self.current_maturity is not None:
                raise ValueError("current_maturity must be null when current_is_na=True")
            if not self.desired_is_na:
                raise ValueError("desired_is_na must be True when current_is_na=True")
            if self.desired_maturity is not None:
                raise ValueError("desired_maturity must be null when desired_is_na=True")
        else:
            if self.current_maturity is None and self.computed_score is None:
                raise ValueError(
                    "current_maturity (or computed_score) required when current_is_na=False"
                )
            if self.desired_is_na:
                raise ValueError("desired_is_na cannot be True when current_is_na=False")

        if not self.desired_is_na:
            if self.desired_maturity is None:
                raise ValueError(
                    "desired_maturity is required when desired_is_na=False"
                )
            if self.current_is_na:
                raise ValueError(
                    "desired_maturity cannot be set when current_is_na=True"
                )
            if self.current_maturity is not None and self.desired_maturity < self.current_maturity:
                raise ValueError("desired_maturity cannot be less than current_maturity")

        return self

    @field_validator("evidence_links", mode="after")
    def sanitise_evidence_links(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = []
        for item in value:
            if not item:
                continue
            text = item.strip()
            if not text:
                continue
            cleaned.append(text)
        return cleaned or None

    @field_validator("comment")
    def sanitise_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = re.sub(r"<script[^>]*>.*?</script>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        return cleaned


class DatabaseConfigInput(BaseValidationSchema):
    """Validation schema for database configuration."""

    backend: str = Field(..., pattern=r"^(sqlite|mysql)$")
    sqlite_path: str | None = Field(None, max_length=500)
    mysql_host: str | None = Field(None, max_length=255)
    mysql_port: int | None = Field(None, ge=1, le=65535)
    mysql_user: str | None = Field(None, max_length=255)
    mysql_password: str | None = Field(None, max_length=255)
    mysql_db: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_db_config(self):
        """Ensure database configuration is complete for selected backend."""
        if self.backend == "sqlite":
            if not self.sqlite_path:
                self.sqlite_path = "./resilience.db"
        elif self.backend == "mysql":
            missing = []
            if not self.mysql_host:
                missing.append("mysql_host")
            if not self.mysql_port:
                missing.append("mysql_port")
            if not self.mysql_user:
                missing.append("mysql_user")
            if not self.mysql_db:
                missing.append("mysql_db")
            if missing:
                raise ValueError(f"MySQL backend requires: {', '.join(missing)}")

        return self

    @field_validator("sqlite_path")
    def validate_sqlite_path(cls, v):
        """Validate SQLite path format."""
        if v is not None:
            # Basic path validation
            if ".." in v or v.startswith("/"):
                raise ValueError("SQLite path must be relative and secure")
            if not v.endswith(".db"):
                v = v + ".db"
        return v


class DimensionInput(BaseValidationSchema):
    """Validation schema for dimension data."""

    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    def validate_dimension_name(cls, v):
        """Validate dimension name."""
        if not re.match(r"^[a-zA-Z0-9\s\-_&().]+$", v):
            raise ValueError("Dimension name contains invalid characters")
        return v.strip()


class ThemeInput(BaseValidationSchema):
    """Validation schema for theme data."""

    dimension_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    def validate_theme_name(cls, v):
        """Validate theme name."""
        if not re.match(r"^[a-zA-Z0-9\s\-_&().]+$", v):
            raise ValueError("Theme name contains invalid characters")
        return v.strip()


class TopicInput(BaseValidationSchema):
    """Validation schema for topic data."""

    theme_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None)
    impact: str | None = Field(default=None)
    benefits: str | None = Field(default=None)
    basic: str | None = Field(default=None)
    advanced: str | None = Field(default=None)
    evidence: str | None = Field(default=None)
    regulations: str | None = Field(default=None)

    @field_validator("name")
    def validate_topic_name(cls, v):
        """Validate topic name."""
        # More lenient for topics as they can be longer descriptions
        if len(v.strip()) == 0:
            raise ValueError("Topic name cannot be empty")
        return v.strip()


class ExplanationInput(BaseValidationSchema):
    """Validation schema for level explanations."""

    topic_id: int = Field(..., gt=0)
    level: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1, max_length=5000)

    @field_validator("text")
    def validate_explanation_text(cls, v):
        """Validate explanation text."""
        if not v or not v.strip():
            raise ValueError("Explanation text cannot be empty")
        return v.strip()


class SessionCombineInput(BaseValidationSchema):
    """Validation schema for combining sessions."""

    source_session_ids: list[int] = Field(..., min_items=1, max_items=50)
    name: str = Field(..., min_length=1, max_length=255)
    assessor: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=10000)

    @field_validator("source_session_ids")
    def validate_session_ids(cls, v):
        """Validate session IDs list."""
        if len(set(v)) != len(v):
            raise ValueError("Duplicate session IDs are not allowed")
        if any(sid <= 0 for sid in v):
            raise ValueError("All session IDs must be positive integers")
        return v


class ExportFormat(BaseValidationSchema):
    """Validation schema for export formats."""

    format_type: str = Field(..., pattern=r"^(json|xlsx|csv)$")
    include_comments: bool = Field(default=True)
    include_timestamps: bool = Field(default=True)


class FilterInput(BaseValidationSchema):
    """Validation schema for filtering options."""

    dimension_name: str | None = Field(None, max_length=255)
    theme_name: str | None = Field(None, max_length=255)
    current_maturity: int | None = Field(None, ge=1, le=5)
    desired_maturity: int | None = Field(None, ge=1, le=5)
    is_na_only: bool = Field(default=False)
    has_comments: bool = Field(default=False)

    @field_validator("dimension_name", "theme_name")
    def validate_filter_names(cls, v):
        """Validate filter name inputs."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            # Prevent injection attempts
            if re.search(r'[<>\'";\\]', v):
                raise ValueError("Filter contains invalid characters")
        return v


class PaginationInput(BaseValidationSchema):
    """Validation schema for pagination parameters."""

    page: int = Field(1, ge=1, le=1000)
    per_page: int = Field(50, ge=1, le=1000)

    @field_validator("per_page")
    def validate_per_page(cls, v):
        """Ensure reasonable pagination limits."""
        if v > 1000:
            raise ValueError("Cannot request more than 1000 items per page")
        return v


class ValidationErrorDetail(BaseModel):
    """Schema for validation error details."""

    field: str
    message: str
    value: Any = None


class ValidationResponse(BaseModel):
    """Schema for validation responses."""

    success: bool
    errors: list[ValidationErrorDetail] = []
    data: dict[str, Any] | None = None


def validate_input(schema_class: type[BaseModel], data: dict[str, Any]) -> ValidationResponse:
    """
    Centralized validation function that returns structured validation results.

    Args:
        schema_class: Pydantic model class to use for validation
        data: Input data to validate

    Returns:
        ValidationResponse with success status and any errors

    Example:
        >>> result = validate_input(SessionCreationInput, {"name": "Test Session"})
        >>> if result.success:
        ...     validated_data = result.data
        >>> else:
        ...     for error in result.errors:
        ...         print(f"Error in {error.field}: {error.message}")
    """
    try:
        validated = schema_class(**data)
        return ValidationResponse(success=True, data=validated.dict())
    except Exception as e:
        errors = []
        if hasattr(e, "errors"):  # Pydantic validation errors
            for error in e.errors():
                errors.append(
                    ValidationErrorDetail(
                        field=".".join(str(x) for x in error["loc"]),
                        message=error["msg"],
                        value=error.get("input"),
                    )
                )
        else:  # Other validation errors
            errors.append(ValidationErrorDetail(field="general", message=str(e)))

        return ValidationResponse(success=False, errors=errors)
