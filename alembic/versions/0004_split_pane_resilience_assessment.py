"""introduce dual maturity ratings and progress tracking

Revision ID: 0004_split_pane_resilience_assessment
Revises: 0003_add_descriptions_and_theme_guidance
Create Date: 2025-10-05 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "0004_split_pane_resilience_assessment"
down_revision = "0003_add_descriptions_and_theme_guidance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    false_expr = sa.sql.expression.false()
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_checks = {constraint.get("name") for constraint in inspector.get_check_constraints("assessment_entries")}

    with op.batch_alter_table("assessment_entries", schema=None) as batch_op:
        batch_op.alter_column("rating_level", new_column_name="current_maturity")
        batch_op.alter_column("is_na", new_column_name="current_is_na")
        batch_op.add_column(
            sa.Column("desired_maturity", sa.Integer(), nullable=True),
        )
        batch_op.add_column(
            sa.Column(
                "desired_is_na",
                sa.Boolean(),
                nullable=False,
                server_default=false_expr,
            )
        )
        batch_op.add_column(sa.Column("evidence_links", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "progress_state",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'not_started'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        if "ck_entry_scores" in existing_checks:
            batch_op.drop_constraint("ck_entry_scores", type_="check")
        batch_op.create_check_constraint(
            "ck_entry_scores",
            "(current_maturity IS NULL OR (current_maturity BETWEEN 1 AND 5)) "
            "AND (desired_maturity IS NULL OR (desired_maturity BETWEEN 1 AND 5)) "
            "AND (computed_score IS NULL OR (computed_score >= 0 AND computed_score <= 5))",
        )
        batch_op.create_foreign_key(
            "fk_assessment_entries_desired_maturity_rating_scale",
            "rating_scale",
            ["desired_maturity"],
            ["level"],
            ondelete="RESTRICT",
        )

    op.execute(
        sa.text(
            """
            UPDATE assessment_entries
            SET
                desired_maturity = current_maturity,
                desired_is_na = current_is_na,
                progress_state = CASE
                    WHEN current_is_na = 1 OR current_maturity IS NOT NULL THEN 'complete'
                    ELSE 'not_started'
                END,
                updated_at = created_at
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("assessment_entries", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_assessment_entries_desired_maturity_rating_scale",
            type_="foreignkey",
        )
        batch_op.drop_constraint("ck_entry_scores", type_="check")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("progress_state")
        batch_op.drop_column("evidence_links")
        batch_op.drop_column("desired_is_na")
        batch_op.drop_column("desired_maturity")
        batch_op.alter_column("current_is_na", new_column_name="is_na")
        batch_op.alter_column("current_maturity", new_column_name="rating_level")
        batch_op.create_check_constraint(
            "ck_entry_scores",
            "(rating_level IS NULL OR (rating_level BETWEEN 1 AND 5)) "
            "AND (computed_score IS NULL OR (computed_score >= 0 AND computed_score <= 5))",
        )
