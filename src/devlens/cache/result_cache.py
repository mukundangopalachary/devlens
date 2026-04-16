from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from devlens.storage.tables import LLMCacheEntry


def get_cached_response(
    session: Session,
    prompt_hash: str,
    cache_kind: str,
) -> str | None:
    statement = select(LLMCacheEntry).where(
        LLMCacheEntry.prompt_hash == prompt_hash,
        LLMCacheEntry.cache_kind == cache_kind,
    )
    entry = session.execute(statement).scalar_one_or_none()
    return None if entry is None else entry.response_text


def store_cached_response(
    session: Session,
    prompt_hash: str,
    cache_kind: str,
    model_name: str,
    prompt_text: str,
    response_text: str,
) -> None:
    entry = LLMCacheEntry(
        prompt_hash=prompt_hash,
        cache_kind=cache_kind,
        model_name=model_name,
        prompt_text=prompt_text,
        response_text=response_text,
    )
    session.add(entry)
    session.flush()
