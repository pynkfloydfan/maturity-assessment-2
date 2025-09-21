"""add descriptions and theme guidance

Revision ID: 619a67d956f6
Revises: 0002_computed_score
Create Date: 2025-09-21 12:58:00.000000

"""

from __future__ import annotations

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "619a67d956f6"
down_revision = "0002_computed_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dimensions: descriptions and image metadata
    op.add_column("dimensions", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("dimensions", sa.Column("image_filename", sa.String(length=255), nullable=True))
    op.add_column("dimensions", sa.Column("image_alt", sa.String(length=255), nullable=True))

    # Themes: description and category
    op.add_column("themes", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("themes", sa.Column("category", sa.String(length=255), nullable=True))

    # Topics: description
    op.add_column("topics", sa.Column("description", sa.Text(), nullable=True))

    # Rating scale: high-level definition
    op.add_column("rating_scale", sa.Column("description", sa.Text(), nullable=True))

    # Theme-level generic guidance table
    op.create_table(
        "theme_level_guidance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("theme_id", "level", name="uq_theme_level"),
        sa.CheckConstraint("level >= 1 AND level <= 5", name="ck_theme_level_range"),
    )
    op.create_index(
        "ix_theme_level_guidance_theme_id", "theme_level_guidance", ["theme_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_theme_level_guidance_theme_id", table_name="theme_level_guidance")
    op.drop_table("theme_level_guidance")

    op.drop_column("rating_scale", "description")
    op.drop_column("topics", "description")
    op.drop_column("themes", "category")
    op.drop_column("themes", "description")
    op.drop_column("dimensions", "image_alt")
    op.drop_column("dimensions", "image_filename")
    op.drop_column("dimensions", "description")

