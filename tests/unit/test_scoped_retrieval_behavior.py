from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import devlens.chat.service as chat_service


def test_scoped_retrieval_preserves_session_filter(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        chat_service,
        "get_settings",
        lambda: SimpleNamespace(
            resolved_project_root=Path(".").resolve(),
            ollama_model="gemma2:2b",
            cache_enabled=False,
            ollama_num_ctx=2048,
            ollama_chat_num_predict=128,
            ollama_keep_alive="5m",
        ),
    )
    monkeypatch.setattr(chat_service, "build_session_memory_summary", lambda *_a, **_k: "mem")
    monkeypatch.setattr(chat_service, "list_recent_messages", lambda *_a, **_k: [])
    monkeypatch.setattr(chat_service, "get_cached_response", lambda *_a, **_k: None)
    monkeypatch.setattr(chat_service, "add_chat_message", lambda *_a, **_k: None)
    monkeypatch.setattr(chat_service, "_refresh_session_memory_summary", lambda *_a, **_k: None)
    monkeypatch.setattr(chat_service, "_build_context", lambda *_a, **_k: "ctx")
    monkeypatch.setattr(chat_service, "_build_history_text", lambda *_a, **_k: "hist")
    monkeypatch.setattr(chat_service, "_unique_paths", lambda *_a, **_k: [])
    monkeypatch.setattr(chat_service, "_citation_labels", lambda *_a, **_k: [])
    monkeypatch.setattr(chat_service, "_extract_chat_text", lambda *_a, **_k: "ok")
    monkeypatch.setattr(chat_service.ollama, "chat", lambda *_a, **_k: {"response": "ok"})

    def fake_retrieve(*_a: object, **kwargs: object) -> list[tuple[object, object, float]]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(chat_service, "retrieve_relevant_chunks", fake_retrieve)

    class _Session:
        def commit(self) -> None:
            return None

    chat_service.answer_question_scoped(
        _Session(),
        session_id=42,
        question="x",
        file_path="src/devlens/health.py",
        debug_retrieval=False,
    )

    assert captured["session_id"] == 42
    assert "src/devlens/health.py" in str(captured["file_path"])
