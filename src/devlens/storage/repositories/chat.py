from __future__ import annotations

from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from devlens.storage.tables import ChatMessage, ChatSession


def create_chat_session(session: Session, title: str = "DevLens Chat") -> ChatSession:
    chat_session = ChatSession(title=title)
    session.add(chat_session)
    session.flush()
    return chat_session


def add_chat_message(
    session: Session,
    session_id: int,
    role: str,
    content: str,
) -> ChatMessage:
    message = ChatMessage(session_id=session_id, role=role, content=content)
    session.add(message)
    session.flush()
    return message


def list_recent_messages(session: Session, session_id: int, limit: int = 8) -> list[ChatMessage]:
    statement = (
        select(ChatMessage)
        .where(
            ChatMessage.session_id == session_id,
            ChatMessage.role != "memory",
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    rows = list(cast(list[ChatMessage], session.execute(statement).scalars().all()))
    rows.reverse()
    return rows


def get_session_memory_summary(session: Session, session_id: int) -> str | None:
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.role == "memory")
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    message = session.execute(statement).scalar_one_or_none()
    if message is None:
        return None
    return message.content


def set_session_memory_summary(session: Session, session_id: int, summary: str) -> None:
    session.execute(
        delete(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.role == "memory",
        )
    )
    session.add(ChatMessage(session_id=session_id, role="memory", content=summary))
    session.flush()


def list_chat_sessions(session: Session, limit: int = 20) -> list[ChatSession]:
    statement = select(ChatSession).order_by(ChatSession.created_at.desc()).limit(limit)
    return list(cast(list[ChatSession], session.execute(statement).scalars().all()))
