"""
Data backup and restore functionality for the resilience assessment application.

Provides comprehensive backup and restore capabilities with validation,
compression, and integrity checking.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..infrastructure.config import get_settings
from ..infrastructure.exceptions import DatabaseError, ResilienceAssessmentError, ValidationError
from ..infrastructure.logging import get_logger, log_operation
from ..infrastructure.repositories import (
    DimensionRepo,
    EntryRepo,
    ExplanationRepo,
    RatingScaleRepo,
    SessionRepo,
    ThemeRepo,
    TopicRepo,
)

logger = get_logger(__name__)


@dataclass
class BackupMetadata:
    """
    Metadata for backup files.

    Contains information about the backup creation, source database,
    and verification checksums.

    Example:
        >>> metadata = BackupMetadata(
        ...     version="1.0",
        ...     created_at=datetime.utcnow(),
        ...     database_backend="sqlite"
        ... )
    """

    version: str
    created_at: datetime
    database_backend: str
    application_version: str
    total_sessions: int
    total_entries: int
    total_topics: int
    checksum: str | None = None
    compressed: bool = False
    backup_type: str = "full"  # "full" or "incremental"


class BackupService:
    """
    Service for creating and restoring database backups.

    Handles full database backups with metadata, compression, and integrity
    verification. Supports both JSON and binary formats.

    Example:
        >>> service = BackupService(session)
        >>> backup_path = service.create_backup("./backups/")
        >>> print(f"Backup created: {backup_path}")
    """

    def __init__(self, session: Session):
        """
        Initialize backup service with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.logger = get_logger(self.__class__.__name__)
        self.settings = get_settings()

    @log_operation("create_backup")
    def create_backup(
        self,
        backup_dir: str | Path,
        filename: str | None = None,
        compress: bool = True,
        include_metadata: bool = True,
    ) -> Path:
        """
        Create a complete database backup.

        Args:
            backup_dir: Directory to store the backup file
            filename: Custom filename (auto-generated if None)
            compress: Whether to compress the backup file
            include_metadata: Whether to include backup metadata

        Returns:
            Path to the created backup file

        Raises:
            DatabaseError: If backup creation fails
            ValidationError: If parameters are invalid

        Example:
            >>> service = BackupService(session)
            >>> backup_path = service.create_backup(
            ...     "./backups",
            ...     filename="assessment_backup_2024.json.gz",
            ...     compress=True
            ... )
        """
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = "json.gz" if compress else "json"
            filename = f"resilience_backup_{timestamp}.{extension}"

        backup_path = backup_dir / filename

        try:
            self.logger.info(f"Starting backup creation: {backup_path}")

            # Collect all data
            backup_data = self._collect_backup_data()

            # Add metadata if requested
            if include_metadata:
                metadata = self._create_backup_metadata(backup_data, compress)
                backup_data["_metadata"] = asdict(metadata)

            # Serialize to JSON
            json_data = json.dumps(backup_data, indent=2, default=str, ensure_ascii=False)

            # Calculate checksum
            checksum = hashlib.sha256(json_data.encode("utf-8")).hexdigest()

            # Update metadata with checksum
            if include_metadata:
                backup_data["_metadata"]["checksum"] = checksum
                json_data = json.dumps(backup_data, indent=2, default=str, ensure_ascii=False)

            # Write to file (compressed or uncompressed)
            if compress:
                with gzip.open(backup_path, "wt", encoding="utf-8") as f:
                    f.write(json_data)
            else:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(json_data)

            self.logger.info(
                f"Backup created successfully: {backup_path} ({backup_path.stat().st_size} bytes)"
            )
            return backup_path

        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}", exc_info=True)
            # Clean up partial backup file
            if backup_path.exists():
                backup_path.unlink()
            raise DatabaseError(f"Backup creation failed: {str(e)}", "create_backup") from e

    @log_operation("restore_backup")
    def restore_backup(
        self, backup_path: str | Path, verify_integrity: bool = True, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Restore database from a backup file.

        Args:
            backup_path: Path to the backup file
            verify_integrity: Whether to verify backup integrity
            dry_run: If True, validate backup but don't restore data

        Returns:
            Dictionary with restoration statistics

        Raises:
            ValidationError: If backup file is invalid
            DatabaseError: If restoration fails

        Example:
            >>> service = BackupService(session)
            >>> stats = service.restore_backup("./backups/backup.json.gz")
            >>> print(f"Restored {stats['sessions_restored']} sessions")
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise ValidationError("backup_path", f"Backup file not found: {backup_path}")

        try:
            self.logger.info(f"Starting backup restoration: {backup_path}")

            # Load backup data
            backup_data = self._load_backup_data(backup_path)

            # Verify integrity if requested
            if verify_integrity:
                self._verify_backup_integrity(backup_data, backup_path)

            # Extract metadata
            metadata = backup_data.get("_metadata", {})
            self.logger.info(f"Restoring backup from {metadata.get('created_at', 'unknown time')}")

            if dry_run:
                self.logger.info("Dry run mode: validation complete, no data restored")
                return self._get_backup_statistics(backup_data)

            # Clear existing data (with confirmation in production)
            if self.settings.app.environment == "production":
                self.logger.warning("Production restore requires explicit confirmation")
                raise ValidationError(
                    "environment", "Production restore requires explicit confirmation parameter"
                )

            # Perform restoration
            stats = self._restore_data(backup_data)

            self.logger.info(f"Backup restoration completed: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"Failed to restore backup: {str(e)}", exc_info=True)
            if isinstance(e, ResilienceAssessmentError):
                raise
            raise DatabaseError(f"Backup restoration failed: {str(e)}", "restore_backup") from e

    def list_backups(self, backup_dir: str | Path) -> list[dict[str, Any]]:
        """
        List all backup files in a directory with metadata.

        Args:
            backup_dir: Directory containing backup files

        Returns:
            List of backup information dictionaries

        Example:
            >>> service = BackupService(session)
            >>> backups = service.list_backups("./backups")
            >>> for backup in backups:
            ...     print(f"{backup['filename']}: {backup['created_at']}")
        """
        backup_dir = Path(backup_dir)

        if not backup_dir.exists():
            return []

        backups = []
        backup_extensions = [".json", ".json.gz"]

        for file_path in backup_dir.iterdir():
            if file_path.is_file() and any(
                str(file_path).endswith(ext) for ext in backup_extensions
            ):
                try:
                    # Try to load metadata
                    backup_data = self._load_backup_data(file_path)
                    metadata = backup_data.get("_metadata", {})

                    backup_info = {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "created_at": metadata.get("created_at"),
                        "total_sessions": metadata.get("total_sessions", 0),
                        "total_entries": metadata.get("total_entries", 0),
                        "backup_type": metadata.get("backup_type", "unknown"),
                        "compressed": metadata.get("compressed", False),
                        "version": metadata.get("version", "unknown"),
                    }

                    backups.append(backup_info)

                except Exception as e:
                    self.logger.warning(f"Failed to read backup metadata for {file_path}: {str(e)}")
                    # Add basic file info even if metadata can't be read
                    backups.append(
                        {
                            "filename": file_path.name,
                            "path": str(file_path),
                            "size": file_path.stat().st_size,
                            "created_at": None,
                            "total_sessions": None,
                            "total_entries": None,
                            "backup_type": "unknown",
                            "compressed": str(file_path).endswith(".gz"),
                            "version": "unknown",
                            "error": str(e),
                        }
                    ) 

        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return backups

    def verify_backup(self, backup_path: str | Path) -> dict[str, Any]:
        """
        Verify backup file integrity and contents.

        Args:
            backup_path: Path to backup file to verify

        Returns:
            Dictionary with verification results

        Example:
            >>> service = BackupService(session)
            >>> result = service.verify_backup("./backups/backup.json.gz")
            >>> if result["valid"]:
            ...     print("Backup is valid")
        """
        backup_path = Path(backup_path)
        result = {"valid": False, "errors": [], "warnings": [], "metadata": {}, "statistics": {}}

        try:
            # Load backup data
            backup_data = self._load_backup_data(backup_path)
            result["statistics"] = self._get_backup_statistics(backup_data)

            # Verify integrity
            self._verify_backup_integrity(backup_data, backup_path)

            # Extract and validate metadata
            metadata = backup_data.get("_metadata", {})
            result["metadata"] = metadata

            # Additional validations
            if not metadata:
                result["warnings"].append("No metadata found in backup")

            if metadata.get("version") != "1.0":
                result["warnings"].append(f"Unknown backup version: {metadata.get('version')}")

            result["valid"] = True
            self.logger.info(f"Backup verification successful: {backup_path}")

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Backup verification failed: {str(e)}")

        return result

    def _collect_backup_data(self) -> dict[str, Any]:
        """Collect all database data for backup."""
        data = {}

        try:
            # Collect all dimensions
            dim_repo = DimensionRepo(self.session)
            dimensions = dim_repo.list()
            data["dimensions"] = [
                {"id": dim.id, "name": dim.name, "created_at": dim.created_at.isoformat()}
                for dim in dimensions
            ]

            # Collect all themes
            theme_repo = ThemeRepo(self.session)
            all_themes = []
            for dim in dimensions:
                themes = theme_repo.list_by_dimension(dim.id)
                for theme in themes:
                    all_themes.append(
                        {
                            "id": theme.id,
                            "dimension_id": theme.dimension_id,
                            "name": theme.name,
                            "created_at": theme.created_at.isoformat(),
                        }
                    )
            data["themes"] = all_themes

            # Collect all topics
            topic_repo = TopicRepo(self.session)
            all_topics = topic_repo.list_all()
            data["topics"] = [
                {
                    "id": topic.id,
                    "theme_id": topic.theme_id,
                    "name": topic.name,
                    "created_at": topic.created_at.isoformat(),
                }
                for topic in all_topics
            ]

            # Collect rating scales
            rating_repo = RatingScaleRepo(self.session)
            scales = rating_repo.list_all()
            data["rating_scales"] = [
                {"level": scale.level, "label": scale.label} for scale in scales
            ]

            # Collect explanations
            exp_repo = ExplanationRepo(self.session)
            all_explanations = []
            for topic in all_topics:
                explanations = exp_repo.list_for_topic(topic.id)
                for exp in explanations:
                    all_explanations.append(
                        {
                            "id": exp.id,
                            "topic_id": exp.topic_id,
                            "level": exp.level,
                            "text": exp.text,
                        }
                    )
            data["explanations"] = all_explanations

            # Collect assessment sessions
            session_repo = SessionRepo(self.session)
            sessions = session_repo.list_all()
            data["sessions"] = [
                {
                    "id": sess.id,
                    "name": sess.name,
                    "assessor": sess.assessor,
                    "organization": sess.organization,
                    "notes": sess.notes,
                    "created_at": sess.created_at.isoformat(),
                }
                for sess in sessions
            ]

            # Collect assessment entries
            entry_repo = EntryRepo(self.session)
            all_entries = []
            for sess in sessions:
                entries = entry_repo.list_for_session(sess.id)
                for entry in entries:
                    all_entries.append(
                        {
                            "id": entry.id,
                            "session_id": entry.session_id,
                            "topic_id": entry.topic_id,
                            "rating_level": entry.rating_level,
                            "computed_score": (
                                float(entry.computed_score) if entry.computed_score else None
                            ),
                            "is_na": entry.is_na,
                            "comment": entry.comment,
                            "created_at": entry.created_at.isoformat(),
                        }
                    )
            data["entries"] = all_entries

            self.logger.info(
                f"Collected backup data: {len(sessions)} sessions, {len(all_entries)} entries"
            )
            return data

        except Exception as e:
            self.logger.error(f"Failed to collect backup data: {str(e)}")
            raise 

    def _create_backup_metadata(
        self, backup_data: dict[str, Any], compressed: bool
    ) -> BackupMetadata:
        """Create backup metadata from collected data."""
        return BackupMetadata(
            version="1.0",
            created_at=datetime.utcnow(),
            database_backend=self.settings.database.backend,
            application_version=self.settings.app.version,
            total_sessions=len(backup_data.get("sessions", [])),
            total_entries=len(backup_data.get("entries", [])),
            total_topics=len(backup_data.get("topics", [])),
            compressed=compressed,
            backup_type="full",
        )

    def _load_backup_data(self, backup_path: Path) -> dict[str, Any]:
        """Load backup data from file."""
        try:
            if str(backup_path).endswith(".gz"):
                with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(backup_path, encoding="utf-8") as f:
                    data = json.load(f)

            return data

        except json.JSONDecodeError as e:
            raise ValidationError("backup_format", f"Invalid JSON in backup file: {str(e)}")
        except Exception as e:
            raise DatabaseError(f"Failed to load backup file: {str(e)}", "load_backup") from e

    def _verify_backup_integrity(self, backup_data: dict[str, Any], backup_path: Path) -> None:
        """Verify backup integrity using checksum."""
        metadata = backup_data.get("_metadata", {})
        stored_checksum = metadata.get("checksum")

        if not stored_checksum:
            self.logger.warning("No checksum found in backup metadata")
            return

        # Remove metadata and calculate checksum
        data_copy = backup_data.copy()
        data_copy.pop("_metadata", None)

        json_data = json.dumps(data_copy, indent=2, default=str, ensure_ascii=False)
        calculated_checksum = hashlib.sha256(json_data.encode("utf-8")).hexdigest()

        if stored_checksum != calculated_checksum:
            raise ValidationError(
                "checksum",
                f"Backup integrity check failed. File may be corrupted. "
                f"Expected: {stored_checksum}, Got: {calculated_checksum}",
            )

        self.logger.info("Backup integrity verification passed")

    def _restore_data(self, backup_data: dict[str, Any]) -> dict[str, Any]:
        """Restore data from backup."""
        stats = {
            "dimensions_restored": 0,
            "themes_restored": 0,
            "topics_restored": 0,
            "sessions_restored": 0,
            "entries_restored": 0,
            "rating_scales_restored": 0,
            "explanations_restored": 0,
        }

        try:
            # Clear existing data (in transaction)
            self.session.execute(text("DELETE FROM assessment_entries"))
            self.session.execute(text("DELETE FROM assessment_sessions"))
            self.session.execute(text("DELETE FROM explanations"))
            self.session.execute(text("DELETE FROM topics"))
            self.session.execute(text("DELETE FROM themes"))
            self.session.execute(text("DELETE FROM dimensions"))
            self.session.execute(text("DELETE FROM rating_scale"))

            # Restore rating scales first
            for scale_data in backup_data.get("rating_scales", []):
                rating_repo = RatingScaleRepo(self.session)
                rating_repo.upsert(scale_data["level"], scale_data["label"])
                stats["rating_scales_restored"] += 1

            # Restore dimensions
            dim_repo = DimensionRepo(self.session)
            for dim_data in backup_data.get("dimensions", []):
                dim_repo.create(dim_data["name"])
                stats["dimensions_restored"] += 1

            # Restore themes
            theme_repo = ThemeRepo(self.session)
            for theme_data in backup_data.get("themes", []):
                theme_repo.create(theme_data["dimension_id"], theme_data["name"])
                stats["themes_restored"] += 1

            # Restore topics
            topic_repo = TopicRepo(self.session)
            for topic_data in backup_data.get("topics", []):
                topic_repo.create(topic_data["theme_id"], topic_data["name"])
                stats["topics_restored"] += 1

            # Restore explanations
            exp_repo = ExplanationRepo(self.session)
            for exp_data in backup_data.get("explanations", []):
                exp_repo.create(exp_data["topic_id"], exp_data["level"], exp_data["text"])
                stats["explanations_restored"] += 1

            # Restore sessions
            session_repo = SessionRepo(self.session)
            for sess_data in backup_data.get("sessions", []):
                session_repo.create(
                    sess_data["name"],
                    sess_data.get("assessor"),
                    sess_data.get("organization"),
                    sess_data.get("notes"),
                )
                stats["sessions_restored"] += 1

            # Restore entries
            entry_repo = EntryRepo(self.session)
            for entry_data in backup_data.get("entries", []):
                computed_score = None
                if entry_data.get("computed_score") is not None:
                    from decimal import Decimal

                    computed_score = Decimal(str(entry_data["computed_score"]))

                entry_repo.upsert(
                    session_id=entry_data["session_id"],
                    topic_id=entry_data["topic_id"],
                    rating_level=entry_data.get("rating_level"),
                    computed_score=computed_score,
                    is_na=entry_data.get("is_na", False),
                    comment=entry_data.get("comment"),
                )
                stats["entries_restored"] += 1

            self.session.commit()
            self.logger.info(f"Data restoration completed: {stats}")
            return stats

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to restore data: {str(e)}")
            raise

    def _get_backup_statistics(self, backup_data: dict[str, Any]) -> dict[str, int]:
        """Get statistics from backup data."""
        return {
            "dimensions": len(backup_data.get("dimensions", [])),
            "themes": len(backup_data.get("themes", [])),
            "topics": len(backup_data.get("topics", [])),
            "sessions": len(backup_data.get("sessions", [])),
            "entries": len(backup_data.get("entries", [])),
            "rating_scales": len(backup_data.get("rating_scales", [])),
            "explanations": len(backup_data.get("explanations", [])),
        }


# Convenience functions
def create_backup(session: Session, backup_dir: str, **kwargs) -> Path:
    """
    Create a database backup (convenience function).

    Args:
        session: Database session
        backup_dir: Directory to store backup
        **kwargs: Additional options for BackupService.create_backup

    Returns:
        Path to created backup file

    Example:
        >>> backup_path = create_backup(session, "./backups", compress=True)
    """
    service = BackupService(session)
    return service.create_backup(backup_dir, **kwargs)


def restore_backup(session: Session, backup_path: str, **kwargs) -> dict[str, Any]:
    """
    Restore database from backup (convenience function).

    Args:
        session: Database session
        backup_path: Path to backup file
        **kwargs: Additional options for BackupService.restore_backup

    Returns:
        Restoration statistics

    Example:
        >>> stats = restore_backup(session, "./backups/backup.json.gz")
    """
    service = BackupService(session)
    return service.restore_backup(backup_path, **kwargs)
