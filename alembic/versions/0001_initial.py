"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-08-17 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dimensions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "rating_scale",
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("level"),
    )
    op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dimension_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dimension_id"], ["dimensions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dimension_id", "name", name="uq_theme_dimension_name"),
    )
    op.create_index("ix_themes_dimension_id", "themes", ["dimension_id"], unique=False)

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("theme_id", "name", name="uq_topic_theme_name"),
    )
    op.create_index("ix_topics_theme_id", "topics", ["theme_id"], unique=False)

    op.create_table(
        "explanations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["level"], ["rating_scale.level"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_explanations_topic_id", "explanations", ["topic_id"], unique=False)
    op.create_index("ix_explanations_level", "explanations", ["level"], unique=False)

    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("assessor", sa.String(length=255), nullable=True),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "assessment_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("rating_level", sa.Integer(), nullable=True),
        sa.Column("is_na", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rating_level"], ["rating_scale.level"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "topic_id", name="uq_session_topic"),
    )
    op.create_index(
        "ix_assessment_entries_session_id", "assessment_entries", ["session_id"], unique=False
    )
    op.create_index(
        "ix_assessment_entries_topic_id", "assessment_entries", ["topic_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_entries_topic_id", table_name="assessment_entries")
    op.drop_index("ix_assessment_entries_session_id", table_name="assessment_entries")
    op.drop_table("assessment_entries")
    op.drop_table("assessment_sessions")
    op.drop_index("ix_explanations_level", table_name="explanations")
    op.drop_index("ix_explanations_topic_id", table_name="explanations")
    op.drop_table("explanations")
    op.drop_index("ix_topics_theme_id", table_name="topics")
    op.drop_table("topics")
    op.drop_index("ix_themes_dimension_id", table_name="themes")
    op.drop_table("themes")
    op.drop_table("rating_scale")
    op.drop_table("dimensions")
