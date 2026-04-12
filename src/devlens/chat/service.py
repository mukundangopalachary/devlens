from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import ollama
from sqlalchemy.orm import Session

from devlens.analysis.llm.client import analyze_with_llm
from devlens.cache.prompt_cache import build_prompt_hash
from devlens.cache.result_cache import get_cached_response, store_cached_response
from devlens.config import get_settings
from devlens.core.schemas import ChatReply, ScheduledTaskPayload, StaticAnalysisMetrics
from devlens.ingestion.file_scanner import scan_specific_files
from devlens.retrieval.qdrant_store import qdrant_available
from devlens.storage.repositories.chat import (
    add_chat_message,
    create_chat_session,
    list_recent_messages,
)
from devlens.storage.repositories.knowledge import (
    create_scheduled_task,
    list_scheduled_tasks,
    mark_task_done,
    remove_task,
    retrieve_relevant_chunks,
    upsert_knowledge_document,
)


def ingest_files_into_knowledge_base(session: Session, file_paths: list[Path]) -> list[str]:
    scan_results = scan_specific_files(file_paths)
    stored_files: list[str] = []
    for scan_result in scan_results:
        upsert_knowledge_document(
            session=session,
            file_path=str(scan_result.relative_path),
            content_hash=scan_result.content_hash,
            title=scan_result.relative_path.name,
            content=scan_result.content,
        )
        stored_files.append(str(scan_result.relative_path))
        _schedule_tasks_for_file(session, scan_result.relative_path, scan_result.content)
    session.commit()
    return stored_files


def start_chat_session(session: Session) -> int:
    chat_session = create_chat_session(session)
    session.commit()
    return chat_session.id


def answer_question(session: Session, session_id: int, question: str) -> ChatReply:
    settings = get_settings()
    chunks = retrieve_relevant_chunks(session, question, limit=2)
    context = "\n\n".join(
        f"[{document.file_path}]\n{chunk.content}" for document, chunk, _ in chunks
    )
    history = list_recent_messages(session, session_id=session_id, limit=4)
    history_text = "\n".join(f"{message.role}: {message.content}" for message in history)
    prompt = (
        "You are DevLens local coding tutor. Answer normal coding questions directly. "
        "Use provided knowledge base context when relevant. If context weak, say so plainly.\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Knowledge context:\n{context}\n\n"
        f"User question: {question}"
    )
    prompt_hash = build_prompt_hash("chat", settings.ollama_model, prompt)
    cached = get_cached_response(session, prompt_hash, cache_kind="chat")
    if cached is not None:
        reply = ChatReply(
            reply=cached,
            fallback_used=False,
            matched_chunks=_unique_paths(chunks),
        )
        add_chat_message(session, session_id, "user", question)
        add_chat_message(session, session_id, "assistant", reply.reply)
        session.commit()
        return reply

    try:
        response = cast(
            dict[str, Any],
            ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                options={"temperature": 0.2},
            ),
        )
        reply_text = str(response.get("response", "")).strip()
        if not reply_text:
            raise ValueError("Empty chat response.")
        if settings.cache_enabled:
            store_cached_response(
                session=session,
                prompt_hash=prompt_hash,
                cache_kind="chat",
                model_name=settings.ollama_model,
                prompt_text=prompt,
                response_text=reply_text,
            )
        reply = ChatReply(
            reply=reply_text,
            fallback_used=False,
            matched_chunks=_unique_paths(chunks),
        )
    except Exception:
        reply = ChatReply(
            reply=_fallback_chat_reply(question, chunks),
            fallback_used=True,
            matched_chunks=_unique_paths(chunks),
        )

    add_chat_message(session, session_id, "user", question)
    add_chat_message(session, session_id, "assistant", reply.reply)
    session.commit()
    return reply


def get_task_lines(session: Session, limit: int = 10) -> list[str]:
    tasks = list_scheduled_tasks(session, limit=limit)
    return [
        f"#{task.id} | {task.priority.upper()} | {task.status} | "
        f"{task.related_file_path or '-'} | {task.title}"
        for task in tasks
    ]


def get_chat_status_line() -> str:
    settings = get_settings()
    vector_mode = (
        "qdrant"
        if settings.vector_backend == "qdrant" and qdrant_available()
        else "sqlite-fallback"
    )
    cache_mode = "on" if settings.cache_enabled else "off"
    return (
        f"model={settings.ollama_model} | embed={settings.ollama_embedding_model} | "
        f"vector={vector_mode} | cache={cache_mode}"
    )


def complete_task(session: Session, task_id: int) -> bool:
    success = mark_task_done(session, task_id)
    session.commit()
    return success


def delete_task(session: Session, task_id: int) -> bool:
    success = remove_task(session, task_id)
    session.commit()
    return success


def _schedule_tasks_for_file(session: Session, relative_path: Path, content: str) -> None:
    llm_result = analyze_with_llm(
        session=session,
        source=content,
        metrics=StaticAnalysisMetrics(),
        issues=[],
    )
    task_payloads = _task_payloads_from_llm(str(relative_path), llm_result.critique)
    for payload in task_payloads:
        create_scheduled_task(session, payload)


def _task_payloads_from_llm(file_path: str, critique: str) -> list[ScheduledTaskPayload]:
    critique_lower = critique.lower()
    payloads: list[ScheduledTaskPayload] = []
    if "complex" in critique_lower or "nest" in critique_lower:
        payloads.append(
            ScheduledTaskPayload(
                title="Reduce control-flow complexity",
                description="Refactor branching and nesting in this file.",
                related_file_path=file_path,
                priority="high",
                due_in_days=2,
            )
        )
    if "long function" in critique_lower:
        payloads.append(
            ScheduledTaskPayload(
                title="Split long function",
                description="Extract smaller helpers from oversized function blocks.",
                related_file_path=file_path,
                priority="medium",
                due_in_days=3,
            )
        )
    if not payloads:
        payloads.append(
            ScheduledTaskPayload(
                title="Review file design",
                description="Write down one improvement and one open question for this file.",
                related_file_path=file_path,
                priority="low",
                due_in_days=4,
            )
        )
    return payloads[:3]


def _fallback_chat_reply(
    question: str,
    chunks: Sequence[tuple[object, object, float]],
) -> str:
    if not chunks:
        return (
            "Fallback answer. Knowledge base empty or model unavailable. "
            "You can still ask general coding questions, but answer quality drops."
        )
    top_context = chunks[0][1]
    top_content = getattr(top_context, "content", "")
    return (
        "Fallback answer. Best matching knowledge chunk says:\n"
        f"{top_content[:700]}\n\n"
        f"Question was: {question}"
    )


def _unique_paths(chunks: Sequence[tuple[object, object, float]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for document, _, _ in chunks:
        file_path = str(getattr(document, "file_path", ""))
        if file_path and file_path not in seen:
            seen.add(file_path)
            ordered.append(file_path)
    return ordered
