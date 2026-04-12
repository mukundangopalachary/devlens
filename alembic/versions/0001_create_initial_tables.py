"""create initial tables

Revision ID: 0001_create_initial_tables
Revises:
Create Date: 2026-04-12 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_create_initial_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "code_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("project_root", sa.String(length=1024), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("code_content", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_code_submissions_file_path", "code_submissions", ["file_path"])
    op.create_index("ix_code_submissions_content_hash", "code_submissions", ["content_hash"])

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("structural_json", sa.Text(), nullable=False),
        sa.Column("llm_json", sa.Text(), nullable=False),
        sa.Column("complexity_score", sa.Float(), nullable=False),
        sa.Column("issues_json", sa.Text(), nullable=False),
        sa.Column("analysis_version", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["code_submissions.id"]),
    )
    op.create_index("ix_analysis_results_submission_id", "analysis_results", ["submission_id"])

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("current_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_skills_name", "skills", ["name"], unique=True)

    op.create_table(
        "skill_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_score", sa.Float(), nullable=False),
        sa.Column("new_score", sa.Float(), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
    )
    op.create_index("ix_skill_history_skill_id", "skill_history", ["skill_id"])

    op.create_table(
        "feedback_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_result_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=64), nullable=True),
        sa.Column("related_skill", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["analysis_result_id"], ["analysis_results.id"]),
    )
    op.create_index(
        "ix_feedback_items_analysis_result_id",
        "feedback_items",
        ["analysis_result_id"],
    )
    op.create_index("ix_feedback_items_kind", "feedback_items", ["kind"])

    op.create_table(
        "mistake_patterns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("mistake_patterns")
    op.drop_index("ix_feedback_items_kind", table_name="feedback_items")
    op.drop_index("ix_feedback_items_analysis_result_id", table_name="feedback_items")
    op.drop_table("feedback_items")
    op.drop_index("ix_skill_history_skill_id", table_name="skill_history")
    op.drop_table("skill_history")
    op.drop_index("ix_skills_name", table_name="skills")
    op.drop_table("skills")
    op.drop_index("ix_analysis_results_submission_id", table_name="analysis_results")
    op.drop_table("analysis_results")
    op.drop_index("ix_code_submissions_content_hash", table_name="code_submissions")
    op.drop_index("ix_code_submissions_file_path", table_name="code_submissions")
    op.drop_table("code_submissions")
