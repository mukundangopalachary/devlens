"""add knowledge metadata filters

Revision ID: 0003_add_knowledge_metadata_filters
Revises: 0002_add_chat_cache_knowledge_tasks
Create Date: 2026-04-13 12:40:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_add_knowledge_metadata_filters"
down_revision = "0002_add_chat_cache_knowledge_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents",
        sa.Column("project_root", sa.String(length=1024), nullable=True),
    )
    op.create_index(
        "ix_knowledge_documents_project_root",
        "knowledge_documents",
        ["project_root"],
    )

    op.add_column(
        "knowledge_chunks",
        sa.Column("session_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_knowledge_chunks_session_id", "knowledge_chunks", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_session_id", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "session_id")

    op.drop_index("ix_knowledge_documents_project_root", table_name="knowledge_documents")
    op.drop_column("knowledge_documents", "project_root")
