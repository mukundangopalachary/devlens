from devlens.chat.service import (
    _build_context,
    _build_history_text,
    _citation_labels,
    _classify_error_code,
    _combine_errors,
    _enforce_citation_presence,
    _migration_hint_from_error,
    _parse_cached_chat_reply,
)


class _Doc:
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path


class _Chunk:
    def __init__(self, chunk_index: int, content: str) -> None:
        self.chunk_index = chunk_index
        self.content = content


class _Message:
    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


def test_citation_labels_contains_file_and_chunk() -> None:
    labels = _citation_labels([(_Doc("src/a.py"), _Chunk(2, "x"), 0.9)])
    assert labels == ["src/a.py#chunk2"]


def test_build_context_trims_total_chars() -> None:
    chunks = [(_Doc("a.py"), _Chunk(0, "x" * 3000), 0.8)]
    context = _build_context(chunks, max_total_chars=200)
    assert len(context) <= 200


def test_build_history_text_trims_from_end() -> None:
    messages = [
        _Message("user", "u" * 800),
        _Message("assistant", "a" * 800),
    ]
    text = _build_history_text(messages, max_chars=300)
    assert len(text) <= 300


def test_migration_hint_for_schema_error() -> None:
    hint = _migration_hint_from_error("no such column: knowledge_documents.project_root")
    assert "alembic upgrade head" in hint


def test_combine_errors_merges_both() -> None:
    merged = _combine_errors("first", "second")
    assert merged == "first | second"


def test_enforce_citation_presence_appends_sources() -> None:
    text = _enforce_citation_presence("answer", ["src/x.py#chunk1"])
    assert "Sources:" in text


def test_classify_error_code_schema_outdated() -> None:
    code = _classify_error_code("no such column: knowledge_documents.project_root")
    assert code == "schema_outdated"


def test_parse_cached_chat_reply_handles_legacy_text() -> None:
    parsed = _parse_cached_chat_reply("plain cached answer")
    assert parsed["reply"] == "plain cached answer"
    assert parsed["fallback_used"] is False
