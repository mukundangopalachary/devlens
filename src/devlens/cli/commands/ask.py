from __future__ import annotations

import json
from typing import Annotated

import typer

from devlens.chat.service import (
    answer_question,
    answer_question_scoped,
    start_chat_session,
    stream_answer_question,
)
from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal

QuestionArgument = Annotated[str, typer.Argument(help="Question to ask DevLens.")]


def ask_command(
    question: QuestionArgument,
    session_id: int | None = typer.Option(
        None, "--session-id", help="Reuse existing chat session id."
    ),
    stream: bool = typer.Option(False, "--stream", help="Stream answer tokens."),
    file_scope: str | None = typer.Option(
        None,
        "--file-scope",
        help="Restrict retrieval to one file path.",
    ),
    debug_retrieval: bool = typer.Option(
        False,
        "--debug-retrieval",
        help="Show retrieval scoring/debug metadata.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    session = SessionLocal()
    try:
        resolved_session_id = session_id if session_id is not None else start_chat_session(session)
        if stream:
            streamed_token_count, reply = stream_answer_question(
                session,
                session_id=resolved_session_id,
                question=question,
                on_token=lambda token: typer.echo(token, nl=False),
            )
            retrieval_debug: list[dict[str, object]] = []
            typer.echo("")
        else:
            streamed_token_count = 0
            if file_scope is not None or debug_retrieval:
                reply, retrieval_debug = answer_question_scoped(
                    session,
                    session_id=resolved_session_id,
                    question=question,
                    file_path=file_scope,
                    debug_retrieval=debug_retrieval,
                )
            else:
                reply = answer_question(session, session_id=resolved_session_id, question=question)
                retrieval_debug = []
    except Exception as exc:
        if as_json:
            emit_json_error(
                "ask",
                "ask_failed",
                "Ask command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "ask",
            {
                "session_id": resolved_session_id,
                "question": question,
                "reply": reply.reply,
                "fallback_used": reply.fallback_used,
                "matched_chunks": reply.matched_chunks,
                "citations": reply.citations,
                "error_reason": reply.error_reason,
                "error_code": reply.error_code,
                "streamed_tokens": streamed_token_count,
                "file_scope": file_scope,
                "retrieval_debug": retrieval_debug,
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    if not stream:
        typer.echo(reply.reply)
    if reply.matched_chunks:
        typer.echo(f"[context] {', '.join(reply.matched_chunks)}")
    if reply.citations:
        typer.echo(f"[citations] {', '.join(reply.citations)}")
    if reply.error_reason:
        typer.echo(f"[error] {reply.error_reason}")
    if reply.error_code:
        typer.echo(f"[error_code] {reply.error_code}")
    if retrieval_debug:
        typer.echo("[retrieval_debug]")
        for row in retrieval_debug:
            typer.echo(
                f"- {row['file_path']}#chunk{row['chunk_index']} score={row['score']} "
                f"terms={row['matched_terms']}"
            )
    typer.echo("[mode] fallback" if reply.fallback_used else "[mode] llm")
