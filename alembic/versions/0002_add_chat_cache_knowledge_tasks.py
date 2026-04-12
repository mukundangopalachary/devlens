"""add chat cache knowledge tasks

Revision ID: 0002_add_chat_cache_knowledge_tasks
Revises: 0001_create_initial_tables
Create Date: 2026-04-12 00:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_add_chat_cache_knowledge_tasks"
down_revision = "0001_create_initial_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_cache_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_hash", sa.String(length=128), nullable=False),
        sa.Column("cache_kind", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("prompt_hash"),
    )
    op.create_index(
        "ix_llm_cache_entries_prompt_hash",
        "llm_cache_entries",
        ["prompt_hash"],
        unique=True,
    )
    op.create_index("ix_llm_cache_entries_cache_kind", "llm_cache_entries", ["cache_kind"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("file_path"),
    )
    op.create_index(
        "ix_knowledge_documents_file_path",
        "knowledge_documents",
        ["file_path"],
        unique=True,
    )
    op.create_index("ix_knowledge_documents_content_hash", "knowledge_documents", ["content_hash"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])

    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("related_file_path", sa.String(length=1024), nullable=True),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scheduled_tasks_related_file_path",
        "scheduled_tasks",
        ["related_file_path"],
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_index("ix_scheduled_tasks_related_file_path", table_name="scheduled_tasks")
    op.drop_table("scheduled_tasks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents_content_hash", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_file_path", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    op.drop_index("ix_llm_cache_entries_cache_kind", table_name="llm_cache_entries")
    op.drop_index("ix_llm_cache_entries_prompt_hash", table_name="llm_cache_entries")
    op.drop_table("llm_cache_entries")
