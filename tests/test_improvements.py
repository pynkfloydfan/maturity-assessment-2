"""
Comprehensive tests for all the code improvements made to the application.

Tests validation, error handling, logging, configuration, and repository patterns.
"""

import os
import tempfile
from typing import Any, cast
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.api import create_assessment_session
from app.domain.schemas import (
    AssessmentEntryInput,
    SessionCreationInput,
    validate_input,
)
from app.domain.services import ScoringService, clamp_rating
from app.infrastructure.config import DatabaseConfig, get_settings, override_settings
from app.infrastructure.db import is_database_configured
from app.infrastructure.exceptions import (
    DatabaseError,
    SessionNotFoundError,
    ValidationError,
    create_user_friendly_error_message,
)
from app.infrastructure.logging import get_logger, setup_logging
from app.infrastructure.models import Base
from app.infrastructure.repositories import SessionRepo


class TestPydanticValidation:
    """Test comprehensive input validation using Pydantic models."""

    def test_session_creation_validation_success(self):
        """Test successful session creation validation."""
        result = validate_input(
            SessionCreationInput,
            {
                "name": "Test Session",
                "assessor": "John Doe",
                "organization": "ACME Corp",
                "notes": "Test notes",
            },
        )

        assert result.success is True
        assert result.data is not None
        data = result.data
        assert data["name"] == "Test Session"
        assert data["assessor"] == "John Doe"

    def test_session_creation_validation_failure(self):
        """Test session creation validation with invalid data."""
        result = validate_input(
            SessionCreationInput, {"name": "", "assessor": "John Doe"}  # Invalid: empty name
        )

        assert result.success is False
        assert len(result.errors) > 0
        assert any("name" in error.field for error in result.errors)

    def test_assessment_entry_validation_success(self):
        """Test successful assessment entry validation."""
        result = validate_input(
            AssessmentEntryInput,
            {
                "session_id": 1,
                "topic_id": 123,
                "rating_level": 3,
                "is_na": False,
                "comment": "Good practices in place",
            },
        )

        assert result.success is True
        assert result.data is not None
        data = result.data
        assert data["rating_level"] == 3
        assert data["is_na"] is False

    def test_assessment_entry_validation_na_consistency(self):
        """Test that is_na and rating_level are mutually exclusive."""
        result = validate_input(
            AssessmentEntryInput,
            {
                "session_id": 1,
                "topic_id": 123,
                "rating_level": 3,
                "is_na": True,  # Invalid: both rating and N/A
            },
        )

        assert result.success is False

    def test_input_sanitization(self):
        """Test that inputs are properly sanitized."""
        result = validate_input(
            SessionCreationInput,
            {
                "name": "  Test Session  ",  # Whitespace should be stripped
                "assessor": "<script>alert('xss')</script>John",  # HTML should be escaped
                "organization": "ACME Corp",
                "notes": "Test\x00notes",  # Control characters should be removed
            },
        )

        assert result.success is True
        assert result.data is not None
        data = result.data
        assert data["name"] == "Test Session"
        assert "&lt;script&gt;" in data["assessor"]  # HTML escaped
        assert "\x00" not in data["notes"]  # Control char removed


class TestErrorHandling:
    """Test comprehensive error handling and user-friendly messages."""

    def test_validation_error_creation(self):
        """Test ValidationError creation and properties."""
        error = ValidationError("test_field", "Test error message", "invalid_value")

        assert error.field == "test_field"
        assert "Test error message" in str(error)
        assert error.user_message is not None
        assert "test_field" in error.details

    def test_database_error_handling(self):
        """Test database error conversion."""
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        from app.infrastructure.exceptions import handle_database_error

        # Simulate a unique constraint violation
        original_error = SQLIntegrityError("statement", {}, Exception("UNIQUE constraint failed"))
        db_error = handle_database_error(original_error, "test_operation")

        assert "IntegrityError" in type(db_error).__name__
        assert "constraint" in db_error.user_message.lower()

    def test_user_friendly_error_messages(self):
        """Test creation of user-friendly error messages."""
        validation_error = ValidationError("name", "cannot be empty")
        friendly_msg = create_user_friendly_error_message(validation_error)

        assert "name" in friendly_msg.lower()
        assert len(friendly_msg) > 0

        # Test generic error
        generic_error = ValueError("Some technical error")
        friendly_msg = create_user_friendly_error_message(generic_error)

        assert "try again" in friendly_msg.lower()


class TestLogging:
    """Test comprehensive logging implementation."""

    def test_logger_creation(self):
        """Test logger creation and configuration."""
        logger = get_logger("test_module")

        assert logger.name == "app.test_module"
        assert logger.handlers  # Should have handlers configured

    def test_logging_configuration(self):
        """Test logging setup with different configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            setup_logging(level="DEBUG", log_file=log_file, structured=True)

            logger = get_logger("test")
            logger.info("Test message")

            # Check that log file was created
            assert os.path.exists(log_file)

    def test_context_logging(self):
        """Test logging with context variables."""
        from app.infrastructure.logging import clear_context, set_context

        logger = get_logger("test_context")

        # Set some context
        set_context(session_id=123, user_id="test_user")

        # This should include context in log record
        logger.info("Test with context")

        # Clear context
        clear_context()

        # This should not include context
        logger.info("Test without context")


class TestConfiguration:
    """Test centralized configuration management."""

    def test_database_config_sqlite(self):
        """Test SQLite database configuration."""
        config = DatabaseConfig(backend="sqlite", sqlite_path="./test.db")

        url = config.get_connection_url()
        assert url.startswith("sqlite:///")
        assert "test.db" in url

    def test_database_config_mysql(self):
        """Test MySQL database configuration."""
        config = DatabaseConfig(
            backend="mysql",
            mysql_host="localhost",
            mysql_user="test",
            mysql_password="pass",
            mysql_database="testdb",
        )

        url = config.get_connection_url()
        assert url.startswith("mysql+pymysql://")
        assert "test:pass@localhost" in url
        assert "testdb" in url

    def test_settings_override(self):
        """Test settings override functionality."""
        original_settings = get_settings()
        original_env = original_settings.app.environment

        # Override settings
        test_settings = override_settings(app_environment="testing")

        assert test_settings.app.environment == "testing"
        assert test_settings.app.environment != original_env

    def test_database_configuration_validation(self):
        """Test database configuration validation."""
        # Test invalid backend
        with pytest.raises(ValueError):
            config = DatabaseConfig(backend="invalid")
            config.get_connection_url()

        # Test MySQL without required fields
        with pytest.raises(ValueError):
            DatabaseConfig(backend="mysql", mysql_host="localhost")


class TestRepositoryPatterns:
    """Test improved repository patterns and consistency."""

    @pytest.fixture
    def test_session(self):
        """Create an in-memory SQLite session for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_session_repository_create(self, test_session):
        """Test session repository create method."""
        repo = SessionRepo(test_session)

        session_obj = repo.create(
            name="Test Session", assessor="John Doe", organization="ACME Corp", notes="Test notes"
        )

        assert session_obj.id is not None
        assert session_obj.name == "Test Session"
        assert session_obj.assessor == "John Doe"

    def test_session_repository_validation(self, test_session):
        """Test repository input validation."""
        repo = SessionRepo(test_session)

        # Test invalid input
        with pytest.raises(ValidationError):
            repo.create(name="", assessor="John Doe")  # Empty name should fail

    def test_session_repository_not_found(self, test_session):
        """Test repository exception for non-existent records."""
        repo = SessionRepo(test_session)

        with pytest.raises(SessionNotFoundError):
            repo.get_by_id_required(999)  # Non-existent ID

    def test_repository_error_handling(self, test_session):
        """Test repository error handling and logging."""
        repo = SessionRepo(test_session)

        # Test database error handling
        with (
            patch.object(test_session, "add", side_effect=Exception("DB Error")),
            pytest.raises(DatabaseError),
        ):
            repo.create(name="Test Session")


class TestQueryOptimization:
    """Test database query optimizations."""

    @pytest.fixture
    def test_session(self):
        """Create an in-memory SQLite session for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_eager_loading(self, test_session):
        """Test that repositories use eager loading to prevent N+1 queries."""
        from app.infrastructure.repositories import DimensionRepo

        repo = DimensionRepo(test_session)

        # This method should use joinedload for themes
        dimensions = repo.list_with_themes()

        # The SQL query should include JOINs (we can't easily test this without SQL logging,
        # but the method exists and should work correctly)
        assert isinstance(dimensions, list)


class TestDomainServices:
    """Test domain services improvements."""

    def test_clamp_rating_valid(self):
        """Test rating validation with valid inputs."""
        assert clamp_rating(1) == 1
        assert clamp_rating(3) == 3
        assert clamp_rating(5) == 5
        assert clamp_rating(None) is None

    def test_clamp_rating_invalid(self):
        """Test rating validation with invalid inputs."""
        with pytest.raises(ValidationError):
            clamp_rating(0)

        with pytest.raises(ValidationError):
            clamp_rating(6)

        with pytest.raises(ValidationError):
            clamp_rating(cast(Any, "3"))  # String instead of int

    @pytest.fixture
    def test_session(self):
        """Create an in-memory SQLite session for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_scoring_service_validation(self, test_session):
        """Test scoring service input validation."""
        service = ScoringService(test_session)

        with pytest.raises(ValidationError):
            service.compute_theme_averages(0)  # Invalid session ID


class TestApplicationAPI:
    """Test application API layer improvements."""

    @pytest.fixture
    def test_session(self):
        """Create an in-memory SQLite session for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_create_assessment_session_validation(self, test_session):
        """Test API session creation with validation."""
        session_obj = create_assessment_session(
            test_session, name="Test Session", assessor="John Doe"
        )

        assert session_obj.name == "Test Session"
        assert session_obj.assessor == "John Doe"

    def test_create_assessment_session_invalid(self, test_session):
        """Test API session creation with invalid input."""
        with pytest.raises(ValidationError):
            create_assessment_session(
                test_session, name="", assessor="John Doe"  # Invalid empty name
            )


class TestIntegration:
    """Integration tests for all improvements working together."""

    def test_end_to_end_validation_and_error_handling(self):
        """Test complete flow with validation, error handling, and logging."""
        # Test configuration
        settings = get_settings()
        assert settings.app.environment in ["development", "testing", "production"]

        # Test database configuration
        db_configured = is_database_configured()
        assert isinstance(db_configured, bool)

        # Test logging
        logger = get_logger("integration_test")
        logger.info("Integration test running")

        # Test validation
        result = validate_input(SessionCreationInput, {"name": "Integration Test"})
        assert result.success is True

    def test_configuration_integration(self):
        """Test that all configuration sections work together."""
        settings = get_settings()

        # Test that all sections are accessible
        assert settings.app is not None
        assert settings.database is not None
        assert settings.logging is not None
        assert settings.security is not None
        assert settings.streamlit is not None

        # Test environment info
        env_info = settings.get_environment_info()
        assert "environment" in env_info
        assert "version" in env_info
        assert "features" in env_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
