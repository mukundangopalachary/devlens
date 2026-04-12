from __future__ import annotations

from typing import cast

from sqlalchemy import select
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
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    rows = list(cast(list[ChatMessage], session.execute(statement).scalars().all()))
    rows.reverse()
    return rows
