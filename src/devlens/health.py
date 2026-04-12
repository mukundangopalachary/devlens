from __future__ import annotations

from pathlib import Path
from sqlite3 import connect
from typing import Any, cast

import ollama

from devlens.config import get_settings
from devlens.retrieval.qdrant_store import qdrant_available


def collect_health_report() -> list[str]:
    settings = get_settings()
    report = [
        f"project_root: {settings.resolved_project_root}",
        f"db_url: {settings.db_url}",
        f"ollama_model: {settings.ollama_model}",
        f"embedding_model: {settings.ollama_embedding_model}",
        f"vector_backend: {settings.vector_backend}",
        f"qdrant_path: {settings.qdrant_path}",
    ]
    report.extend(_ollama_report(settings.ollama_model, settings.ollama_embedding_model))
    report.extend(_database_report(settings.db_url))
    report.extend(_qdrant_report())
    return report


def _ollama_report(chat_model: str, embedding_model: str) -> list[str]:
    try:
        response = cast(dict[str, Any], ollama.list())
        models = response.get("models", [])
        names = {str(item.get("model", "")) for item in cast(list[dict[str, Any]], models)}
        return [
            f"ollama: ok ({len(names)} model(s) visible)",
            f"chat_model_ready: {'yes' if chat_model in names else 'no'}",
            f"embedding_model_ready: {'yes' if embedding_model in names else 'no'}",
        ]
    except Exception as exc:
        return [f"ollama: error ({exc})"]


def _database_report(db_url: str) -> list[str]:
    if not db_url.startswith("sqlite:///"):
        return ["db_check: skipped (only sqlite check implemented)"]

    db_path = Path(db_url.removeprefix("sqlite:///"))
    if not db_path.exists():
        return [f"db_exists: no ({db_path})"]

    with connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        cursor.execute("SELECT version_num FROM alembic_version")
        version_row = cursor.fetchone()

    required_tables = {
        "code_submissions",
        "analysis_results",
        "skills",
        "skill_history",
        "feedback_items",
        "knowledge_documents",
        "knowledge_chunks",
        "scheduled_tasks",
        "chat_sessions",
        "chat_messages",
        "llm_cache_entries",
    }
    missing_tables = sorted(required_tables - tables)
    return [
        f"db_exists: yes ({db_path})",
        f"db_tables_ok: {'yes' if not missing_tables else 'no'}",
        f"db_missing_tables: {', '.join(missing_tables) if missing_tables else '-'}",
        f"alembic_version: {version_row[0] if version_row else 'unknown'}",
    ]


def _qdrant_report() -> list[str]:
    return [f"qdrant_client_installed: {'yes' if qdrant_available() else 'no'}"]
