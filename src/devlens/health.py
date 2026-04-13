from __future__ import annotations

import subprocess
from pathlib import Path
from sqlite3 import connect
from typing import Any, cast

import ollama

from devlens.config import get_settings
from devlens.retrieval.qdrant_store import qdrant_available


def collect_health_snapshot() -> dict[str, object]:
    settings = get_settings()
    checks: dict[str, dict[str, object]] = {
        "gpu": _gpu_report(),
        "ollama": _ollama_report(settings.ollama_model, settings.ollama_embedding_model),
        "database": _database_report(settings.db_url),
        "qdrant": _qdrant_report(
            vector_backend=settings.vector_backend,
            qdrant_path=settings.qdrant_path,
            qdrant_collection=settings.qdrant_collection,
        ),
        "cache": _cache_report(settings.db_url),
    }
    overall_status = _overall_status(*(check["status"] for check in checks.values()))
    return {
        "project_root": str(settings.resolved_project_root),
        "db_url": settings.db_url,
        "ollama_model": settings.ollama_model,
        "embedding_model": settings.ollama_embedding_model,
        "vector_backend": settings.vector_backend,
        "qdrant_path": str(settings.qdrant_path),
        "overall_status": overall_status,
        "checks": checks,
    }


def collect_health_report(snapshot: dict[str, object] | None = None) -> list[str]:
    data = snapshot if snapshot is not None else collect_health_snapshot()
    report = [
        f"project_root: {data['project_root']}",
        f"db_url: {data['db_url']}",
        f"ollama_model: {data['ollama_model']}",
        f"embedding_model: {data['embedding_model']}",
        f"vector_backend: {data['vector_backend']}",
        f"qdrant_path: {data['qdrant_path']}",
        f"overall_status: {data['overall_status']}",
    ]

    checks = cast(dict[str, dict[str, object]], data["checks"])
    for check_name in ("gpu", "ollama", "database", "qdrant", "cache"):
        check = checks[check_name]
        report.append(f"{check_name}: {check['status']} ({check['summary']})")
        details = cast(dict[str, object], check["details"])
        for key, value in details.items():
            report.append(f"  {check_name}.{key}: {value}")

    return report


def _ollama_report(chat_model: str, embedding_model: str) -> dict[str, object]:
    model_names: set[str] = set()
    try:
        response = cast(dict[str, Any], ollama.list())
        models = response.get("models", [])
        model_names = {str(item.get("model", "")) for item in cast(list[dict[str, Any]], models)}
    except Exception as exc:
        return {
            "status": "error",
            "summary": "model list unavailable",
            "details": {
                "list_error": str(exc),
                "chat_model_ready": False,
                "embedding_model_ready": False,
                "chat_endpoint_ok": False,
                "embed_endpoint_ok": False,
            },
        }

    chat_ready = _model_ready(chat_model, model_names)
    embedding_ready = _model_ready(embedding_model, model_names)

    chat_endpoint_ok = False
    chat_error: str | None = None
    try:
        ollama.chat(
            model=chat_model,
            messages=[{"role": "user", "content": "health-check"}],
            options={"temperature": 0, "num_predict": 1},
        )
        chat_endpoint_ok = True
    except Exception as exc:
        chat_error = str(exc)

    embed_endpoint_ok = False
    embed_error: str | None = None
    try:
        ollama.embed(model=embedding_model, input="health-check")
        embed_endpoint_ok = True
    except Exception as exc:
        embed_error = str(exc)

    if chat_endpoint_ok and embed_endpoint_ok and chat_ready and embedding_ready:
        status = "ok"
        summary = "chat+embed ready"
    else:
        status = "warn"
        summary = "chat or embed not ready"

    return {
        "status": status,
        "summary": summary,
        "details": {
            "visible_models": len(model_names),
            "chat_model_ready": chat_ready,
            "embedding_model_ready": embedding_ready,
            "chat_endpoint_ok": chat_endpoint_ok,
            "embed_endpoint_ok": embed_endpoint_ok,
            "chat_error": chat_error,
            "embed_error": embed_error,
        },
    }


def _database_report(db_url: str) -> dict[str, object]:
    if not db_url.startswith("sqlite:///"):
        return {
            "status": "skipped",
            "summary": "sqlite-only check",
            "details": {"reason": "db check implemented for sqlite urls only"},
        }

    db_path = Path(db_url.removeprefix("sqlite:///"))
    if not db_path.exists():
        return {
            "status": "warn",
            "summary": "database missing",
            "details": {"db_exists": False, "db_path": str(db_path)},
        }

    with connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        version_row: tuple[str] | None = None
        if "alembic_version" in tables:
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
    return {
        "status": "ok" if not missing_tables else "warn",
        "summary": "schema ready" if not missing_tables else "schema incomplete",
        "details": {
            "db_exists": True,
            "db_path": str(db_path),
            "db_tables_ok": not missing_tables,
            "db_missing_tables": missing_tables,
            "alembic_version": version_row[0] if version_row else "unknown",
        },
    }


def _qdrant_report(
    vector_backend: str,
    qdrant_path: Path,
    qdrant_collection: str,
) -> dict[str, object]:
    index_counts = _knowledge_index_counts()

    if vector_backend != "qdrant":
        return {
            "status": "ok",
            "summary": "sqlite fallback active",
            "details": {
                "backend": vector_backend,
                "qdrant_client_installed": qdrant_available(),
                "qdrant_active": False,
                "fallback": "sqlite",
                "sqlite_chunks": index_counts["sqlite_chunks"],
            },
        }

    if not qdrant_available():
        return {
            "status": "warn",
            "summary": "fallback active (qdrant client missing)",
            "details": {
                "backend": vector_backend,
                "qdrant_client_installed": False,
                "qdrant_active": False,
                "fallback": "sqlite",
                "sqlite_chunks": index_counts["sqlite_chunks"],
            },
        }

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(path=str(qdrant_path))
        collection_exists = bool(client.collection_exists(qdrant_collection))
        qdrant_points = _qdrant_points_count(client, qdrant_collection) if collection_exists else 0
        return {
            "status": "ok",
            "summary": "qdrant active",
            "details": {
                "backend": vector_backend,
                "qdrant_client_installed": True,
                "qdrant_active": True,
                "collection": qdrant_collection,
                "collection_exists": collection_exists,
                "qdrant_points": qdrant_points,
                "sqlite_chunks": index_counts["sqlite_chunks"],
                "fallback": "none",
            },
        }
    except Exception as exc:
        return {
            "status": "warn",
            "summary": "fallback active (qdrant unavailable)",
            "details": {
                "backend": vector_backend,
                "qdrant_client_installed": True,
                "qdrant_active": False,
                "fallback": "sqlite",
                "sqlite_chunks": index_counts["sqlite_chunks"],
                "error": str(exc),
            },
        }


def _knowledge_index_counts() -> dict[str, int]:
    settings = get_settings()
    db_url = settings.db_url
    if not db_url.startswith("sqlite:///"):
        return {"sqlite_chunks": 0}

    db_path = Path(db_url.removeprefix("sqlite:///"))
    if not db_path.exists():
        return {"sqlite_chunks": 0}

    with connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_chunks'"
        )
        if cursor.fetchone() is None:
            return {"sqlite_chunks": 0}
        cursor.execute("SELECT COUNT(*) FROM knowledge_chunks")
        count = int(cursor.fetchone()[0])
    return {"sqlite_chunks": count}


def _qdrant_points_count(client: Any, collection_name: str) -> int:
    try:
        if hasattr(client, "count"):
            response = client.count(collection_name=collection_name, exact=True)
            if hasattr(response, "count"):
                return int(response.count)
            if isinstance(response, dict) and "count" in response:
                return int(response["count"])
    except Exception:
        return 0
    return 0


def _cache_report(db_url: str) -> dict[str, object]:
    if not db_url.startswith("sqlite:///"):
        return {
            "status": "skipped",
            "summary": "sqlite-only check",
            "details": {"reason": "cache count implemented for sqlite urls only"},
        }

    db_path = Path(db_url.removeprefix("sqlite:///"))
    if not db_path.exists():
        return {
            "status": "warn",
            "summary": "cache table unavailable",
            "details": {"db_exists": False, "db_path": str(db_path), "cache_total": 0},
        }

    with connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_cache_entries'"
        )
        if cursor.fetchone() is None:
            return {
                "status": "warn",
                "summary": "cache table missing",
                "details": {
                    "db_exists": True,
                    "db_path": str(db_path),
                    "cache_table_exists": False,
                    "cache_total": 0,
                },
            }

        cursor.execute("SELECT cache_kind, COUNT(*) FROM llm_cache_entries GROUP BY cache_kind")
        rows = cursor.fetchall()

    counts_by_kind = {str(cache_kind): int(count) for cache_kind, count in rows}
    return {
        "status": "ok",
        "summary": "cache counts ready",
        "details": {
            "db_exists": True,
            "db_path": str(db_path),
            "cache_table_exists": True,
            "cache_total": sum(counts_by_kind.values()),
            "counts_by_kind": counts_by_kind,
        },
    }


def _gpu_report() -> dict[str, object]:
    via_nvidia = _detect_gpu_via_nvidia_smi()
    if via_nvidia:
        return {
            "status": "ok",
            "summary": "gpu detected",
            "details": {
                "gpu_present": True,
                "detection": "nvidia-smi",
                "devices": via_nvidia,
            },
        }

    via_sysfs = _detect_gpu_via_sysfs()
    if via_sysfs:
        return {
            "status": "ok",
            "summary": "gpu detected",
            "details": {
                "gpu_present": True,
                "detection": "sysfs",
                "devices": via_sysfs,
            },
        }

    return {
        "status": "warn",
        "summary": "gpu not detected",
        "details": {
            "gpu_present": False,
            "detection": "none",
            "devices": [],
        },
    }


def _detect_gpu_via_nvidia_smi() -> list[str]:
    try:
        command = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader",
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except Exception:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _detect_gpu_via_sysfs() -> list[str]:
    devices: list[str] = []
    vendor_names = {
        "0x10de": "NVIDIA",
        "0x1002": "AMD",
        "0x1022": "AMD",
        "0x8086": "Intel",
    }
    for vendor_path in sorted(Path("/sys/class/drm").glob("card*/device/vendor")):
        try:
            vendor_raw = vendor_path.read_text(encoding="utf-8").strip().lower()
            device_path = vendor_path.parent / "device"
            device_raw = (
                device_path.read_text(encoding="utf-8").strip().lower()
                if device_path.exists()
                else "unknown"
            )
            vendor_name = vendor_names.get(vendor_raw, vendor_raw)
            devices.append(f"{vendor_name} {device_raw}")
        except Exception:
            continue
    return devices


def _model_ready(expected_model: str, visible_models: set[str]) -> bool:
    if expected_model in visible_models:
        return True
    expected_base = expected_model.split(":", maxsplit=1)[0]
    return any(item.split(":", maxsplit=1)[0] == expected_base for item in visible_models)


def _overall_status(*statuses: object) -> str:
    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "warn" for status in statuses):
        return "warn"
    return "ok"
