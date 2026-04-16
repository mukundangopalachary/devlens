from __future__ import annotations

from hashlib import sha256


def build_prompt_hash(*parts: str) -> str:
    payload = "::".join(parts)
    return sha256(payload.encode("utf-8")).hexdigest()
