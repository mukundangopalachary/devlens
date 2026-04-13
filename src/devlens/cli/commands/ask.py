from __future__ import annotations

import json
from typing import Annotated

import typer

from devlens.chat.service import answer_question, start_chat_session, stream_answer_question
from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal

QuestionArgument = Annotated[str, typer.Argument(help="Question to ask DevLens.")]


def ask_command(
    question: QuestionArgument,
    session_id: int | None = typer.Option(
        None, "--session-id", help="Reuse existing chat session id."
    ),
    stream: bool = typer.Option(False, "--stream", help="Stream answer tokens."),
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
            typer.echo("")
        else:
            streamed_token_count = 0
            reply = answer_question(session, session_id=resolved_session_id, question=question)
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
    typer.echo("[mode] fallback" if reply.fallback_used else "[mode] llm")
