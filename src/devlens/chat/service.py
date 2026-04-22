from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

import ollama
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from devlens.analysis.llm.client import analyze_with_llm
from devlens.cache.prompt_cache import build_prompt_hash
from devlens.cache.result_cache import get_cached_response, store_cached_response
from devlens.config import get_settings
from devlens.core.schemas import ChatReply, ScheduledTaskPayload, StaticAnalysisMetrics
from devlens.ingestion.file_scanner import scan_specific_files
from devlens.retrieval.qdrant_store import qdrant_available
from devlens.security.path_guard import ensure_within_root
from devlens.storage.repositories.chat import (
    add_chat_message,
    create_chat_session,
    get_session_memory_summary,
    list_recent_messages,
    set_session_memory_summary,
)
from devlens.storage.repositories.knowledge import (
    create_scheduled_task,
    list_scheduled_tasks,
    mark_task_done,
    remove_task,
    retrieve_relevant_chunks,
    retrieve_relevant_chunks_with_debug,
    snooze_task,
    update_task_due,
    upsert_knowledge_document,
)
from devlens.storage.tables import ScheduledTask


def ingest_files_into_knowledge_base(
    session: Session,
    file_paths: list[Path],
    *,
    session_id: int | None = None,
) -> list[str]:
    expanded_paths = _expand_add_paths(file_paths)
    scan_results = scan_specific_files(expanded_paths, include_all_extensions=True)
    settings = get_settings()
    stored_files: list[str] = []
    for scan_result in scan_results:
        upsert_knowledge_document(
            session=session,
            file_path=str(scan_result.relative_path),
            content_hash=scan_result.content_hash,
            title=scan_result.relative_path.name,
            content=scan_result.content,
            project_root=str(settings.resolved_project_root),
            session_id=session_id,
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
    chunks, retrieval_error = _safe_retrieve_relevant_chunks(
        session,
        question,
        project_root=str(settings.resolved_project_root),
        session_id=session_id,
    )
    context = _build_context(chunks)
    history = list_recent_messages(session, session_id=session_id, limit=4)
    history_text = _build_history_text(history)
    memory_summary = build_session_memory_summary(session, session_id=session_id)
    prompt = (
        "You are DevLens local-first engineering coach. "
        "Give practical, code-aware help. Be explicit when context weak. "
        "If context supports claims, reference citations exactly as [path#chunk].\n\n"
        f"Session memory summary:\n{memory_summary}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Knowledge context:\n{context}\n\n"
        f"User question: {question}"
    )
    prompt_hash = build_prompt_hash("chat", settings.ollama_model, prompt)
    cached = get_cached_response(session, prompt_hash, cache_kind="chat")
    if cached is not None:
        cached_reply = _parse_cached_chat_reply(cached)
        reply = ChatReply(
            reply=str(cached_reply["reply"]),
            fallback_used=bool(cached_reply["fallback_used"]),
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=retrieval_error,
            error_code=_classify_error_code(retrieval_error),
        )
        add_chat_message(session, session_id, "user", question)
        add_chat_message(session, session_id, "assistant", reply.reply)
        session.commit()
        return reply

    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": "Use citations [path#chunk] when context supports answer.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.2,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": settings.ollama_chat_num_predict,
            },
            keep_alive=settings.ollama_keep_alive,
            stream=False,
        )
        reply_text = _extract_chat_text(response)
        if not reply_text:
            raise ValueError("Empty chat response.")
        reply_text = _enforce_citation_presence(reply_text, _citation_labels(chunks))
        if settings.cache_enabled:
            store_cached_response(
                session=session,
                prompt_hash=prompt_hash,
                cache_kind="chat",
                model_name=settings.ollama_model,
                prompt_text=prompt,
                response_text=json.dumps(
                    {"reply": reply_text, "fallback_used": False, "error_code": None},
                    sort_keys=True,
                ),
            )
        reply = ChatReply(
            reply=reply_text,
            fallback_used=False,
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=retrieval_error,
            error_code=_classify_error_code(retrieval_error),
        )
    except Exception as exc:
        combined_error = _combine_errors(retrieval_error, str(exc))
        reply = ChatReply(
            reply=_fallback_chat_reply(question, chunks),
            fallback_used=True,
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=combined_error,
            error_code=_classify_error_code(combined_error),
        )

    add_chat_message(session, session_id, "user", question)
    add_chat_message(session, session_id, "assistant", reply.reply)
    _refresh_session_memory_summary(session, session_id=session_id)
    session.commit()
    return reply


def answer_question_scoped(
    session: Session,
    *,
    session_id: int,
    question: str,
    file_path: str | None,
    debug_retrieval: bool,
) -> tuple[ChatReply, list[dict[str, object]]]:
    settings = get_settings()
    debug_rows: list[dict[str, object]] = []
    normalized_scope = _normalize_file_scope(file_path, settings.resolved_project_root)
    retrieval_session_id = session_id
    try:
        if debug_retrieval:
            chunks, debug_rows = retrieve_relevant_chunks_with_debug(
                session,
                question,
                limit=2,
                file_path=normalized_scope,
                project_root=str(settings.resolved_project_root),
                session_id=retrieval_session_id,
            )
        else:
            chunks = retrieve_relevant_chunks(
                session,
                question,
                limit=2,
                file_path=normalized_scope,
                project_root=str(settings.resolved_project_root),
                session_id=retrieval_session_id,
            )
    except OperationalError as exc:
        retrieval_error = _migration_hint_from_error(str(exc))
        reply = ChatReply(
            reply=_fallback_chat_reply(question, []),
            fallback_used=True,
            matched_chunks=[],
            citations=[],
            error_reason=retrieval_error,
            error_code=_classify_error_code(retrieval_error),
        )
        return reply, debug_rows

    context = _build_context(chunks)
    history = list_recent_messages(session, session_id=session_id, limit=4)
    history_text = _build_history_text(history)
    memory_summary = build_session_memory_summary(session, session_id=session_id)
    prompt = (
        "You are DevLens local-first engineering coach. "
        "Give practical, code-aware help. Be explicit when context weak. "
        "If context supports claims, reference citations exactly as [path#chunk].\n\n"
        f"Session memory summary:\n{memory_summary}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Knowledge context:\n{context}\n\n"
        f"User question: {question}"
    )
    prompt_hash = build_prompt_hash("chat", settings.ollama_model, prompt)
    cached = get_cached_response(session, prompt_hash, cache_kind="chat")
    if cached is not None:
        cached_reply = _parse_cached_chat_reply(cached)
        reply = ChatReply(
            reply=str(cached_reply["reply"]),
            fallback_used=bool(cached_reply["fallback_used"]),
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=None,
            error_code=None,
        )
        add_chat_message(session, session_id, "user", question)
        add_chat_message(session, session_id, "assistant", reply.reply)
        session.commit()
        return reply, debug_rows

    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": "Use citations [path#chunk] when context supports answer.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.2,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": settings.ollama_chat_num_predict,
            },
            keep_alive=settings.ollama_keep_alive,
            stream=False,
        )
        reply_text = _extract_chat_text(response)
        if not reply_text:
            raise ValueError("Empty chat response.")
        reply_text = _enforce_citation_presence(reply_text, _citation_labels(chunks))
        if settings.cache_enabled:
            store_cached_response(
                session=session,
                prompt_hash=prompt_hash,
                cache_kind="chat",
                model_name=settings.ollama_model,
                prompt_text=prompt,
                response_text=json.dumps(
                    {"reply": reply_text, "fallback_used": False, "error_code": None},
                    sort_keys=True,
                ),
            )
        reply = ChatReply(
            reply=reply_text,
            fallback_used=False,
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=None,
            error_code=None,
        )
    except Exception as exc:
        reason = str(exc)
        reply = ChatReply(
            reply=_fallback_chat_reply(question, chunks),
            fallback_used=True,
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=reason,
            error_code=_classify_error_code(reason),
        )

    add_chat_message(session, session_id, "user", question)
    add_chat_message(session, session_id, "assistant", reply.reply)
    _refresh_session_memory_summary(session, session_id=session_id)
    session.commit()
    return reply, debug_rows


def get_task_lines(session: Session, limit: int = 10, status: str = "open") -> list[str]:
    tasks = list_scheduled_tasks(session, limit=limit)
    filtered_tasks = _filter_tasks(tasks, status=status)
    return [
        f"#{task.id} | {task.priority.upper()} | {task.status} | "
        f"{task.related_file_path or '-'} | {task.title}"
        for task in filtered_tasks
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


def set_task_due_days(session: Session, task_id: int, days: int) -> bool:
    success = update_task_due(session, task_id, days)
    session.commit()
    return success


def snooze_existing_task(session: Session, task_id: int, days: int) -> bool:
    success = snooze_task(session, task_id, days)
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


def _citation_labels(chunks: Sequence[tuple[object, object, float]]) -> list[str]:
    labels: list[str] = []
    for document, chunk, _ in chunks:
        file_path = str(getattr(document, "file_path", ""))
        chunk_index = int(getattr(chunk, "chunk_index", -1))
        if file_path and chunk_index >= 0:
            labels.append(f"{file_path}#chunk{chunk_index}")
    return labels


def _build_history_text(history: Sequence[object], max_chars: int = 1200) -> str:
    lines = [
        f"{getattr(message, 'role', 'unknown')}: {getattr(message, 'content', '')}"
        for message in history
    ]
    text = "\n".join(lines)
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _build_context(
    chunks: Sequence[tuple[object, object, float]],
    *,
    max_chunks: int = 4,
    max_chars_per_chunk: int = 700,
    max_total_chars: int = 2200,
) -> str:
    sections: list[str] = []
    ranked_chunks = sorted(
        list(chunks),
        key=lambda item: (
            float(item[2]),
            len(str(getattr(item[1], "content", ""))),
        ),
        reverse=True,
    )
    total = 0
    seen_signatures: set[str] = set()
    for document, chunk, _ in ranked_chunks[:max_chunks]:
        file_path = str(getattr(document, "file_path", ""))
        chunk_index = int(getattr(chunk, "chunk_index", -1))
        content = str(getattr(chunk, "content", ""))[:max_chars_per_chunk]
        signature = f"{file_path}:{content[:120]}"
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        label = f"{file_path}#chunk{chunk_index}" if chunk_index >= 0 else file_path
        section = f"[{label}]\n{content}"
        if total + len(section) > max_total_chars:
            break
        sections.append(section)
        total += len(section)
    return "\n\n".join(sections)


def _extract_chat_text(response: Any) -> str:
    message_content = _extract_message_content(_extract_field(response, "message"))
    if message_content:
        return message_content

    response_text = _extract_field(response, "response")
    if isinstance(response_text, str):
        return response_text.strip()

    if hasattr(response, "model_dump"):
        dumped = cast(dict[str, Any], response.model_dump())
        return _extract_chat_text(dumped)

    return ""


def _enforce_citation_presence(reply_text: str, citations: Sequence[str]) -> str:
    if not citations:
        return reply_text
    if any(f"[{label}]" in reply_text for label in citations):
        return reply_text
    sources = ", ".join(f"[{label}]" for label in citations)
    return f"{reply_text}\n\nSources: {sources}"


def stream_answer_question(
    session: Session,
    session_id: int,
    question: str,
    *,
    on_token: Callable[[str], None] | None = None,
) -> tuple[int, ChatReply]:
    settings = get_settings()
    chunks, retrieval_error = _safe_retrieve_relevant_chunks(
        session,
        question,
        project_root=str(settings.resolved_project_root),
        session_id=session_id,
    )
    history_text = _build_history_text(
        list_recent_messages(session, session_id=session_id, limit=4)
    )
    memory_summary = build_session_memory_summary(session, session_id=session_id)
    context_text = _build_context(chunks)
    prompt = (
        "You are DevLens local-first engineering coach. "
        "Give practical, code-aware help. "
        "Use citations [path#chunk] when context supports answer.\n\n"
        f"Session memory summary:\n{memory_summary}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Knowledge context:\n{context_text}\n\n"
        f"User question: {question}"
    )

    collected: list[str] = []
    try:
        stream = ollama.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": "Use citations [path#chunk] when context supports answer.",
                },
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": 0.2,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": settings.ollama_chat_num_predict,
            },
            keep_alive=settings.ollama_keep_alive,
            stream=True,
        )
        for chunk in cast(Sequence[Any], stream):
            token = _extract_stream_token(chunk)
            if token:
                collected.append(token)
                if on_token is not None:
                    on_token(token)

        reply_text = "".join(collected).strip()
        if not reply_text:
            raise ValueError("Empty chat stream response.")
        reply_text = _enforce_citation_presence(reply_text, _citation_labels(chunks))

        prompt_hash = build_prompt_hash("chat", settings.ollama_model, prompt)
        if settings.cache_enabled:
            store_cached_response(
                session=session,
                prompt_hash=prompt_hash,
                cache_kind="chat",
                model_name=settings.ollama_model,
                prompt_text=prompt,
                response_text=json.dumps(
                    {"reply": reply_text, "fallback_used": False, "error_code": None},
                    sort_keys=True,
                ),
            )

        reply = ChatReply(
            reply=reply_text,
            fallback_used=False,
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=retrieval_error,
            error_code=_classify_error_code(retrieval_error),
        )
    except Exception as exc:
        combined_error = _combine_errors(retrieval_error, str(exc))
        reply = ChatReply(
            reply=_fallback_chat_reply(question, chunks),
            fallback_used=True,
            matched_chunks=_unique_paths(chunks),
            citations=_citation_labels(chunks),
            error_reason=combined_error,
            error_code=_classify_error_code(combined_error),
        )

    add_chat_message(session, session_id, "user", question)
    add_chat_message(session, session_id, "assistant", reply.reply)
    _refresh_session_memory_summary(session, session_id=session_id)
    session.commit()
    return len(collected), reply


def build_session_memory_summary(session: Session, session_id: int, limit: int = 12) -> str:
    persisted = get_session_memory_summary(session, session_id=session_id)
    if persisted:
        return persisted

    history = list_recent_messages(session, session_id=session_id, limit=limit)
    if not history:
        return "No prior context in this session."
    user_topics: list[str] = []
    assistant_actions: list[str] = []
    for message in history:
        content = getattr(message, "content", "").strip().replace("\n", " ")
        snippet = content[:120]
        if getattr(message, "role", "") == "user":
            user_topics.append(snippet)
        elif getattr(message, "role", "") == "assistant":
            assistant_actions.append(snippet)
    return json.dumps(
        {
            "recent_user_topics": user_topics[-5:],
            "recent_assistant_points": assistant_actions[-5:],
        },
        sort_keys=True,
    )


def _refresh_session_memory_summary(session: Session, session_id: int) -> None:
    history = list_recent_messages(session, session_id=session_id, limit=12)
    if not history:
        return

    user_topics: list[str] = []
    assistant_points: list[str] = []
    for message in history:
        content = getattr(message, "content", "").strip().replace("\n", " ")
        snippet = content[:120]
        if getattr(message, "role", "") == "user":
            user_topics.append(snippet)
        elif getattr(message, "role", "") == "assistant":
            assistant_points.append(snippet)

    summary = json.dumps(
        {
            "recent_user_topics": user_topics[-5:],
            "recent_assistant_points": assistant_points[-5:],
        },
        sort_keys=True,
    )
    set_session_memory_summary(session, session_id=session_id, summary=summary)


def _safe_retrieve_relevant_chunks(
    session: Session,
    question: str,
    *,
    project_root: str,
    session_id: int,
) -> tuple[list[tuple[object, object, float]], str | None]:
    try:
        chunks = retrieve_relevant_chunks(
            session,
            question,
            limit=2,
            project_root=project_root,
            session_id=session_id,
        )
        return list(chunks), None
    except OperationalError as exc:
        message = _migration_hint_from_error(str(exc))
        return [], message


def _migration_hint_from_error(error_text: str) -> str:
    markers = (
        "knowledge_documents.project_root",
        "knowledge_chunks.session_id",
    )
    if any(marker in error_text for marker in markers):
        return "Knowledge schema outdated. Run: uv run alembic upgrade head"
    return error_text


def _combine_errors(first: str | None, second: str | None) -> str | None:
    if first and second:
        return f"{first} | {second}"
    return first or second


def _classify_error_code(error_text: str | None) -> str | None:
    if not error_text:
        return None
    lowered = error_text.lower()
    if "alembic upgrade head" in lowered or "no such column" in lowered:
        return "schema_outdated"
    if "timeout" in lowered:
        return "timeout"
    if "connection" in lowered or "refused" in lowered:
        return "network_unavailable"
    if "empty chat" in lowered:
        return "empty_model_response"
    return "runtime_error"


def _parse_cached_chat_reply(cached: str) -> dict[str, object]:
    try:
        parsed = json.loads(cached)
    except Exception:
        return {"reply": cached, "fallback_used": False, "error_code": None}
    if isinstance(parsed, dict) and isinstance(parsed.get("reply"), str):
        return {
            "reply": parsed["reply"],
            "fallback_used": bool(parsed.get("fallback_used", False)),
            "error_code": parsed.get("error_code"),
        }
    return {"reply": cached, "fallback_used": False, "error_code": None}


def _extract_stream_token(chunk: Any) -> str:
    message_content = _extract_message_content(_extract_field(chunk, "message"))
    if message_content:
        return message_content
    direct_response = _extract_field(chunk, "response")
    if isinstance(direct_response, str):
        return direct_response
    return ""


def _extract_message_content(message: Any) -> str:
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        return ""
    content_attr = getattr(message, "content", None)
    if isinstance(content_attr, str):
        return content_attr.strip()
    return ""


def _extract_field(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _expand_add_paths(file_paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in file_paths:
        normalized = str(path)
        if normalized.startswith("@"):
            normalized = normalized[1:]
        candidate = Path(normalized or ".")
        if candidate.is_dir():
            expanded.extend(sorted(item for item in candidate.rglob("*") if item.is_file()))
            continue
        expanded.append(candidate)
    return expanded


def _normalize_file_scope(file_path: str | None, project_root: Path) -> str | None:
    if file_path is None:
        return None
    raw = file_path.strip()
    if not raw:
        return None
    candidate = Path(raw[1:]) if raw.startswith("@") else Path(raw)
    # Try resolving within project root first
    try:
        safe_path = ensure_within_root(candidate, project_root)
        relative = str(safe_path.relative_to(project_root))
        if relative:
            return relative
    except (ValueError, Exception):
        pass
    # Fallback: use the raw path string for substring matching
    return str(candidate)


def _filter_tasks(tasks: Sequence[ScheduledTask], *, status: str) -> list[ScheduledTask]:
    if status == "all":
        return list(tasks)
    if status == "done":
        return [task for task in tasks if task.status == "done"]
    return [task for task in tasks if task.status != "done"]
