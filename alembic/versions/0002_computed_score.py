"""add computed_score to assessment_entries

Revision ID: 0002_computed_score
Revises: 0001_initial
Create Date: 2025-08-17 00:30:00.000000

"""

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "0002_computed_score"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_entries", sa.Column("computed_score", sa.Numeric(3, 2), nullable=True)
    )
    # Update constraint: handled at application level; MySQL won't support altering check constraints prior to 8.0
    # so we don't add a DB-level CHECK in MySQL 5.6; SQLAlchemy model will validate.


def downgrade() -> None:
    op.drop_column("assessment_entries", "computed_score")
