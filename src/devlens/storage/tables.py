from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from devlens.storage.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    project_root: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)

    analysis_results: Mapped[list[AnalysisResult]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("code_submissions.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    structural_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    llm_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    complexity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    issues_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    analysis_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")

    submission: Mapped[CodeSubmission] = relationship(back_populates="analysis_results")
    feedback_items: Mapped[list[FeedbackItem]] = relationship(
        back_populates="analysis_result",
        cascade="all, delete-orphan",
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    current_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    history_entries: Mapped[list[SkillHistory]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
    )


class SkillHistory(Base):
    __tablename__ = "skill_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    previous_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    new_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="initial")

    skill: Mapped[Skill] = relationship(back_populates="history_entries")


class FeedbackItem(Base):
    __tablename__ = "feedback_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_result_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_results.id"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_skill: Mapped[str | None] = mapped_column(String(255), nullable=True)

    analysis_result: Mapped[AnalysisResult] = relationship(back_populates="feedback_items")


class MistakePattern(Base):
    __tablename__ = "mistake_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class LLMCacheEntry(Base):
    __tablename__ = "llm_cache_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    cache_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True, index=True)
    project_root: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    related_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    source_signature: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="DevLens Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


TABLES: tuple[type[Base], ...] = (
    CodeSubmission,
    AnalysisResult,
    Skill,
    SkillHistory,
    FeedbackItem,
    MistakePattern,
    LLMCacheEntry,
    KnowledgeDocument,
    KnowledgeChunk,
    ScheduledTask,
    ChatSession,
    ChatMessage,
)
