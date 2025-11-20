"""add topic metadata columns

Revision ID: 0005_expand_topic_fields
Revises: 0004_split_pane_resilience_assessment
Create Date: 2024-02-14 00:00:00.000000

"""

from __future__ import annotations

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_expand_topic_fields"
down_revision = "0004_split_pane_resilience_assessment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("topics", schema=None) as batch_op:
        batch_op.add_column(sa.Column("impact", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("benefits", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("basic", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("advanced", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("evidence", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("regulations", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("topics", schema=None) as batch_op:
        batch_op.drop_column("regulations")
        batch_op.drop_column("evidence")
        batch_op.drop_column("advanced")
        batch_op.drop_column("basic")
        batch_op.drop_column("benefits")
        batch_op.drop_column("impact")

