from __future__ import annotations


def chunk_text(text: str, max_lines: int = 40, overlap: int = 5) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[str] = []
    start = 0
    step = max(1, max_lines - overlap)
    while start < len(lines):
        chunk = "\n".join(lines[start : start + max_lines]).strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
