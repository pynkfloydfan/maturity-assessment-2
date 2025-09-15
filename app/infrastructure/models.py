from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DimensionORM(Base):
    __tablename__ = "dimensions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    themes: Mapped[list[ThemeORM]] = relationship(back_populates="dimension", cascade="all, delete")


class ThemeORM(Base):
    __tablename__ = "themes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dimension_id: Mapped[int] = mapped_column(
        ForeignKey("dimensions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("dimension_id", "name", name="uq_theme_dimension_name"),)

    dimension: Mapped[DimensionORM] = relationship(back_populates="themes")
    topics: Mapped[list[TopicORM]] = relationship(back_populates="theme", cascade="all, delete")


class TopicORM(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("theme_id", "name", name="uq_topic_theme_name"),)

    theme: Mapped[ThemeORM] = relationship(back_populates="topics")
    explanations: Mapped[list[ExplanationORM]] = relationship(
        back_populates="topic", cascade="all, delete"
    )


class RatingScaleORM(Base):
    __tablename__ = "rating_scale"
    level: Mapped[int] = mapped_column(Integer, primary_key=True)  # 1..5
    label: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (CheckConstraint("level >= 1 AND level <= 5", name="ck_level_range"),)


class ExplanationORM(Base):
    __tablename__ = "explanations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[int] = mapped_column(
        ForeignKey("rating_scale.level", ondelete="RESTRICT"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    topic: Mapped[TopicORM] = relationship(back_populates="explanations")
    # No backref from RatingScaleORM to keep it simple


class AssessmentSessionORM(Base):
    __tablename__ = "assessment_sessions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assessor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    entries: Mapped[list[AssessmentEntryORM]] = relationship(
        back_populates="session", cascade="all, delete"
    )


class AssessmentEntryORM(Base):
    __tablename__ = "assessment_entries"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating_level: Mapped[int | None] = mapped_column(
        ForeignKey("rating_scale.level", ondelete="RESTRICT"), nullable=True
    )
    computed_score: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )  # supports decimal scores (0.00..5.00)
    is_na: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("session_id", "topic_id", name="uq_session_topic"),
        CheckConstraint(
            "(rating_level IS NULL OR (rating_level BETWEEN 1 AND 5)) AND (computed_score IS NULL OR (computed_score >= 0 AND computed_score <= 5))",
            name="ck_entry_scores",
        ),
    )

    session: Mapped[AssessmentSessionORM] = relationship(back_populates="entries")
