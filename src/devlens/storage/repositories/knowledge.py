from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from devlens.analysis.llm.client import embed_text
from devlens.core.schemas import ScheduledTaskPayload
from devlens.ingestion.chunker import chunk_text
from devlens.retrieval.qdrant_store import (
    delete_document_chunks,
    qdrant_available,
    search_chunks,
    upsert_chunk,
)
from devlens.storage.tables import KnowledgeChunk, KnowledgeDocument, ScheduledTask


def upsert_knowledge_document(
    session: Session,
    file_path: str,
    content_hash: str,
    title: str,
    content: str,
) -> KnowledgeDocument:
    statement = select(KnowledgeDocument).where(KnowledgeDocument.file_path == file_path)
    document = session.execute(statement).scalar_one_or_none()
    now = datetime.now(UTC)
    if document is None:
        document = KnowledgeDocument(
            file_path=file_path,
            content_hash=content_hash,
            title=title,
            created_at=now,
            updated_at=now,
        )
        session.add(document)
        session.flush()
    else:
        if document.content_hash == content_hash:
            return document
        document.content_hash = content_hash
        document.title = title
        document.updated_at = now
        session.flush()
        session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
        if qdrant_available():
            delete_document_chunks(document.id)

    for index, chunk in enumerate(chunk_text(content)):
        embedding = embed_text(session, chunk)
        chunk_row = KnowledgeChunk(
            document_id=document.id,
            chunk_index=index,
            content=chunk,
            embedding_json=json.dumps(embedding),
        )
        session.add(chunk_row)
        if embedding and qdrant_available():
            upsert_chunk(
                point_id=f"{document.id}:{index}",
                vector=embedding,
                payload={
                    "document_id": document.id,
                    "chunk_index": index,
                },
            )
    session.flush()
    return document


def retrieve_relevant_chunks(
    session: Session,
    query: str,
    limit: int = 4,
) -> list[tuple[KnowledgeDocument, KnowledgeChunk, float]]:
    query_embedding = embed_text(session, query)
    if qdrant_available() and query_embedding:
        qdrant_rows = search_chunks(query_embedding, limit=limit)
        if qdrant_rows:
            hydrated = _hydrate_qdrant_results(session, qdrant_rows)
            if hydrated:
                return hydrated

    statement = (
        select(KnowledgeDocument, KnowledgeChunk)
        .join(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .order_by(KnowledgeDocument.updated_at.desc())
    )
    rows = session.execute(statement).all()
    scored: list[tuple[KnowledgeDocument, KnowledgeChunk, float]] = []
    for document, chunk in rows:
        chunk_embedding = [float(item) for item in json.loads(chunk.embedding_json)]
        score = _score_similarity(query, query_embedding, chunk.content, chunk_embedding)
        scored.append((document, chunk, score))
    scored.sort(key=lambda item: item[2], reverse=True)
    return scored[:limit]


def _hydrate_qdrant_results(
    session: Session,
    qdrant_rows: list[dict[str, float | int]],
) -> list[tuple[KnowledgeDocument, KnowledgeChunk, float]]:
    hydrated: list[tuple[KnowledgeDocument, KnowledgeChunk, float]] = []
    for row in qdrant_rows:
        statement = (
            select(KnowledgeDocument, KnowledgeChunk)
            .join(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeDocument.id == int(row["document_id"]),
                KnowledgeChunk.chunk_index == int(row["chunk_index"]),
            )
        )
        match = session.execute(statement).first()
        if match is None:
            continue
        document, chunk = match
        hydrated.append((document, chunk, float(row["score"])))
    return hydrated


def create_scheduled_task(
    session: Session,
    payload: ScheduledTaskPayload,
) -> ScheduledTask:
    due_at = datetime.now(UTC) + timedelta(days=payload.due_in_days)
    task = ScheduledTask(
        title=payload.title,
        description=payload.description,
        related_file_path=payload.related_file_path,
        priority=payload.priority,
        due_at=due_at,
    )
    session.add(task)
    session.flush()
    return task


def list_scheduled_tasks(session: Session, limit: int = 10) -> list[ScheduledTask]:
    statement = (
        select(ScheduledTask)
        .order_by(
            ScheduledTask.status.asc(),
            ScheduledTask.due_at.asc(),
            ScheduledTask.created_at.desc(),
        )
        .limit(limit)
    )
    return list(cast(list[ScheduledTask], session.execute(statement).scalars().all()))


def mark_task_done(session: Session, task_id: int) -> bool:
    statement = select(ScheduledTask).where(ScheduledTask.id == task_id)
    task = session.execute(statement).scalar_one_or_none()
    if task is None:
        return False
    task.status = "done"
    session.flush()
    return True


def remove_task(session: Session, task_id: int) -> bool:
    statement = select(ScheduledTask).where(ScheduledTask.id == task_id)
    task = session.execute(statement).scalar_one_or_none()
    if task is None:
        return False
    session.delete(task)
    session.flush()
    return True


def _score_similarity(
    query: str,
    query_embedding: list[float],
    chunk_text_value: str,
    chunk_embedding: list[float],
) -> float:
    if query_embedding and chunk_embedding and len(query_embedding) == len(chunk_embedding):
        return _cosine_similarity(query_embedding, chunk_embedding)
    query_terms = {term for term in query.lower().split() if term}
    chunk_terms = {term for term in chunk_text_value.lower().split() if term}
    if not query_terms:
        return 0.0
    return len(query_terms & chunk_terms) / len(query_terms)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot = float(
        sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
    )
    return float(dot / (left_norm * right_norm))
