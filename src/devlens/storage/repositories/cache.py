from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from devlens.storage.tables import LLMCacheEntry


def clear_cache_by_kind(session: Session, cache_kind: str) -> int:
    session.execute(delete(LLMCacheEntry).where(LLMCacheEntry.cache_kind == cache_kind))
    return 0
