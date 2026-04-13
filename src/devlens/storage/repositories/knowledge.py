from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import cast

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from devlens.analysis.llm.client import embed_text
from devlens.core.schemas import ScheduledTaskPayload
from devlens.ingestion.chunker import chunk_text
from devlens.retrieval.qdrant_store import (
    delete_document_chunks,
    qdrant_available,
    recreate_collection,
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
    *,
    project_root: str | None = None,
    session_id: int | None = None,
) -> KnowledgeDocument:
    statement = select(KnowledgeDocument).where(KnowledgeDocument.file_path == file_path)
    document = session.execute(statement).scalar_one_or_none()
    now = datetime.now(UTC)
    if document is None:
        document = KnowledgeDocument(
            file_path=file_path,
            project_root=project_root,
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
        document.project_root = project_root
        document.content_hash = content_hash
        document.title = title
        document.updated_at = now
        session.flush()
        session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
        if qdrant_available():
            delete_document_chunks(document.id)

    chunk_index = 0
    seen_chunk_hashes: set[str] = set()
    for chunk in chunk_text(content):
        chunk_hash = sha256(chunk.encode("utf-8")).hexdigest()
        if chunk_hash in seen_chunk_hashes:
            continue
        seen_chunk_hashes.add(chunk_hash)

        embedding = embed_text(session, chunk)
        chunk_row = KnowledgeChunk(
            document_id=document.id,
            chunk_index=chunk_index,
            session_id=session_id,
            content=chunk,
            embedding_json=json.dumps(embedding),
        )
        session.add(chunk_row)
        if embedding and qdrant_available():
            upsert_chunk(
                point_id=f"{document.id}:{chunk_index}",
                vector=embedding,
                payload={
                    "document_id": document.id,
                    "chunk_index": chunk_index,
                    "file_path": document.file_path,
                    "project_root": project_root,
                    "session_id": session_id,
                },
            )
        chunk_index += 1
    session.flush()
    return document


def retrieve_relevant_chunks(
    session: Session,
    query: str,
    limit: int = 4,
    *,
    file_path: str | None = None,
    project_root: str | None = None,
    session_id: int | None = None,
) -> list[tuple[KnowledgeDocument, KnowledgeChunk, float]]:
    query_embedding = embed_text(session, query)
    if qdrant_available() and query_embedding:
        qdrant_rows = search_chunks(
            query_embedding,
            limit=limit,
            file_path=file_path,
            project_root=project_root,
            session_id=session_id,
        )
        if qdrant_rows:
            hydrated = _hydrate_qdrant_results(session, qdrant_rows)
            if hydrated:
                return hydrated

    statement = (
        select(KnowledgeDocument, KnowledgeChunk)
        .join(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .order_by(KnowledgeDocument.updated_at.desc())
    )
    if file_path is not None:
        statement = statement.where(KnowledgeDocument.file_path == file_path)
    if project_root is not None:
        statement = statement.where(KnowledgeDocument.project_root == project_root)
    if session_id is not None:
        statement = statement.where(KnowledgeChunk.session_id == session_id)
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
    *,
    source_signature: str | None = None,
) -> ScheduledTask:
    due_at = datetime.now(UTC) + timedelta(days=payload.due_in_days)
    signature = source_signature or _task_source_signature(
        title=payload.title,
        description=payload.description,
        related_file_path=payload.related_file_path,
    )
    existing = session.execute(
        select(ScheduledTask).where(
            ScheduledTask.source_signature == signature,
            ScheduledTask.status != "done",
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    task = ScheduledTask(
        title=payload.title,
        description=payload.description,
        related_file_path=payload.related_file_path,
        priority=payload.priority,
        due_at=due_at,
        source_signature=signature,
    )
    session.add(task)
    session.flush()
    return task


def list_scheduled_tasks(session: Session, limit: int = 10) -> list[ScheduledTask]:
    now = datetime.now(UTC)
    statement = (
        select(ScheduledTask)
        .where(or_(ScheduledTask.snoozed_until.is_(None), ScheduledTask.snoozed_until <= now))
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


def snooze_task(session: Session, task_id: int, days: int) -> bool:
    statement = select(ScheduledTask).where(ScheduledTask.id == task_id)
    task = session.execute(statement).scalar_one_or_none()
    if task is None:
        return False
    task.snoozed_until = datetime.now(UTC) + timedelta(days=days)
    session.flush()
    return True


def update_task_due(session: Session, task_id: int, days: int) -> bool:
    statement = select(ScheduledTask).where(ScheduledTask.id == task_id)
    task = session.execute(statement).scalar_one_or_none()
    if task is None:
        return False
    task.due_at = datetime.now(UTC) + timedelta(days=days)
    session.flush()
    return True


def regenerate_tasks_for_file(
    session: Session,
    file_path: str,
    task_texts: list[str],
) -> int:
    if not task_texts:
        return 0

    created = 0
    for task_text in task_texts:
        payload = ScheduledTaskPayload(
            title=_task_title_from_text(task_text),
            description=task_text,
            related_file_path=file_path,
            priority=_priority_from_task_text(task_text),
            due_in_days=2,
        )
        signature = _task_source_signature(
            title=payload.title,
            description=payload.description,
            related_file_path=payload.related_file_path,
        )
        existing = session.execute(
            select(ScheduledTask).where(
                ScheduledTask.source_signature == signature,
                ScheduledTask.status != "done",
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        create_scheduled_task(session, payload, source_signature=signature)
        created += 1
    return created


def score_task_priority_from_feedback_text(feedback_text: str) -> str:
    lowered = feedback_text.lower()
    high_markers = ("bug", "recursion", "complex", "nest", "critical")
    medium_markers = ("refactor", "split", "optimiz", "improve")
    if any(marker in lowered for marker in high_markers):
        return "high"
    if any(marker in lowered for marker in medium_markers):
        return "medium"
    return "low"


def _task_source_signature(title: str, description: str, related_file_path: str | None) -> str:
    normalized = "|".join(
        [
            (related_file_path or "").strip().lower(),
            title.strip().lower(),
            description.strip().lower(),
        ]
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


def _task_title_from_text(task_text: str) -> str:
    words = [word for word in task_text.strip().split() if word]
    if not words:
        return "Review task"
    return " ".join(words[:6])


def _priority_from_task_text(task_text: str) -> str:
    return score_task_priority_from_feedback_text(task_text)


def reindex_qdrant(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(KnowledgeDocument, KnowledgeChunk)
        .join(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .order_by(KnowledgeDocument.id.asc(), KnowledgeChunk.chunk_index.asc())
    ).all()

    documents = {document.id for document, _ in rows}

    if not qdrant_available():
        return {
            "documents_total": len(documents),
            "chunks_total": len(rows),
            "embedded_chunks": 0,
            "indexed_chunks": 0,
            "skipped_chunks": len(rows),
            "deduplicated_chunks": 0,
        }
    unique_map: dict[tuple[int, str], tuple[KnowledgeDocument, KnowledgeChunk]] = {}
    for document, chunk in rows:
        chunk_hash = sha256(chunk.content.encode("utf-8")).hexdigest()
        unique_map.setdefault((document.id, chunk_hash), (document, chunk))

    unique_rows = list(unique_map.values())
    deduplicated_chunks = len(rows) - len(unique_rows)

    vector_size: int | None = None
    indexed_chunks = 0
    embedded_chunks = 0
    skipped_chunks = 0
    prepared: list[tuple[KnowledgeDocument, KnowledgeChunk, list[float]]] = []

    for document, chunk in unique_rows:
        embedding = [float(item) for item in json.loads(chunk.embedding_json)]
        if not embedding:
            embedding = embed_text(session, chunk.content)
            if embedding:
                chunk.embedding_json = json.dumps(embedding)

        if not embedding:
            skipped_chunks += 1
            continue

        embedded_chunks += 1
        if vector_size is None:
            vector_size = len(embedding)

        if vector_size is not None and len(embedding) != vector_size:
            skipped_chunks += 1
            continue

        prepared.append((document, chunk, embedding))

    if vector_size is not None:
        recreate_collection(vector_size)
        for document, chunk, embedding in prepared:
            if upsert_chunk(
                point_id=f"{document.id}:{chunk.chunk_index}",
                vector=embedding,
                payload={
                    "document_id": document.id,
                    "chunk_index": chunk.chunk_index,
                    "file_path": document.file_path,
                    "project_root": document.project_root,
                    "session_id": chunk.session_id,
                },
            ):
                indexed_chunks += 1
            else:
                skipped_chunks += 1

    session.flush()
    return {
        "documents_total": len(documents),
        "chunks_total": len(rows),
        "embedded_chunks": embedded_chunks,
        "indexed_chunks": indexed_chunks,
        "skipped_chunks": skipped_chunks,
        "deduplicated_chunks": deduplicated_chunks,
    }


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
