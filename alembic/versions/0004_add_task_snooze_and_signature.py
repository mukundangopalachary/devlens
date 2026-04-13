"""add task snooze and signature

Revision ID: 0004_add_task_snooze_and_signature
Revises: 0003_add_knowledge_metadata_filters
Create Date: 2026-04-14 01:20:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_add_task_snooze_and_signature"
down_revision = "0003_add_knowledge_metadata_filters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheduled_tasks",
        sa.Column("source_signature", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_scheduled_tasks_source_signature",
        "scheduled_tasks",
        ["source_signature"],
    )

    op.add_column(
        "scheduled_tasks",
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheduled_tasks", "snoozed_until")
    op.drop_index("ix_scheduled_tasks_source_signature", table_name="scheduled_tasks")
    op.drop_column("scheduled_tasks", "source_signature")
