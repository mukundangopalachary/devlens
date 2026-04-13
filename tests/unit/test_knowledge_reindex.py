import json

from devlens.storage.repositories.knowledge import reindex_qdrant


class _FakeChunk:
    def __init__(
        self,
        chunk_index: int,
        content: str,
        embedding_json: str,
        session_id: int | None = None,
    ) -> None:
        self.chunk_index = chunk_index
        self.content = content
        self.embedding_json = embedding_json
        self.session_id = session_id


class _FakeDocument:
    def __init__(self, doc_id: int, file_path: str, project_root: str | None = None) -> None:
        self.id = doc_id
        self.file_path = file_path
        self.project_root = project_root


class _FakeResult:
    def __init__(self, rows: list[tuple[_FakeDocument, _FakeChunk]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[_FakeDocument, _FakeChunk]]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[tuple[_FakeDocument, _FakeChunk]]) -> None:
        self._rows = rows

    def execute(self, _statement: object) -> _FakeResult:
        return _FakeResult(self._rows)

    def flush(self) -> None:
        return None


def test_reindex_qdrant_reports_deduplicated_chunks(monkeypatch: object) -> None:
    doc = _FakeDocument(doc_id=1, file_path="x.py")
    rows = [
        (doc, _FakeChunk(chunk_index=0, content="same", embedding_json=json.dumps([0.1, 0.2]))),
        (doc, _FakeChunk(chunk_index=1, content="same", embedding_json=json.dumps([0.1, 0.2]))),
    ]
    session = _FakeSession(rows)

    monkeypatch.setattr("devlens.storage.repositories.knowledge.qdrant_available", lambda: False)

    stats = reindex_qdrant(session)

    assert stats["chunks_total"] == 2
    assert stats["indexed_chunks"] == 0
    assert stats["skipped_chunks"] == 2


def test_reindex_qdrant_happy_path(monkeypatch: object) -> None:
    doc = _FakeDocument(doc_id=11, file_path="a.py", project_root="/repo")
    rows = [
        (
            doc,
            _FakeChunk(
                chunk_index=0,
                content="alpha",
                embedding_json=json.dumps([0.1, 0.2]),
                session_id=99,
            ),
        )
    ]
    session = _FakeSession(rows)

    upserts: list[tuple[str, dict[str, object]]] = []
    recreates: list[int] = []

    monkeypatch.setattr("devlens.storage.repositories.knowledge.qdrant_available", lambda: True)
    monkeypatch.setattr(
        "devlens.storage.repositories.knowledge.recreate_collection",
        lambda vector_size: recreates.append(vector_size) or True,
    )
    monkeypatch.setattr(
        "devlens.storage.repositories.knowledge.upsert_chunk",
        lambda point_id, vector, payload: upserts.append((point_id, payload)) or True,
    )

    stats = reindex_qdrant(session)

    assert stats["indexed_chunks"] == 1
    assert recreates == [2]
    assert upserts[0][0] == "11:0"
    assert upserts[0][1]["project_root"] == "/repo"
    assert upserts[0][1]["session_id"] == 99
