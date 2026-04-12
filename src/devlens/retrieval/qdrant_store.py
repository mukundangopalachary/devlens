from __future__ import annotations

from typing import Any, cast

from devlens.config import get_settings

QDRANT_IMPORT_OK = True
try:
    from qdrant_client import QdrantClient, models
except Exception:  # pragma: no cover - optional dependency fallback
    QDRANT_IMPORT_OK = False


def qdrant_available() -> bool:
    return QDRANT_IMPORT_OK


def ensure_collection(vector_size: int) -> bool:
    if not qdrant_available() or vector_size <= 0:
        return False

    client = _get_client()
    collection_name = get_settings().qdrant_collection
    if client.collection_exists(collection_name):
        return True

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    return True


def upsert_chunk(
    point_id: str,
    vector: list[float],
    payload: dict[str, Any],
) -> bool:
    if not qdrant_available() or not vector:
        return False

    ensure_collection(len(vector))
    client = _get_client()
    client.upsert(
        collection_name=get_settings().qdrant_collection,
        points=[
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
        wait=True,
    )
    return True


def delete_document_chunks(document_id: int) -> bool:
    if not qdrant_available():
        return False

    client = _get_client()
    client.delete(
        collection_name=get_settings().qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
        wait=True,
    )
    return True


def search_chunks(
    query_vector: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    if not qdrant_available() or not query_vector:
        return []

    ensure_collection(len(query_vector))
    client = _get_client()
    results = _query_points(client, query_vector, limit)
    if results is None:
        return []

    parsed_results: list[dict[str, Any]] = []
    for item in results:
        payload = cast(dict[str, Any], item.payload or {})
        parsed_results.append(
            {
                "document_id": int(payload["document_id"]),
                "chunk_index": int(payload["chunk_index"]),
                "score": float(item.score),
            }
        )
    return parsed_results


def _get_client() -> Any:
    settings = get_settings()
    return QdrantClient(path=str(settings.qdrant_path))


def _query_points(client: Any, query_vector: list[float], limit: int) -> Any:
    collection_name = get_settings().qdrant_collection

    if hasattr(client, "query_points"):
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
        if hasattr(response, "points"):
            return response.points
        return response

    if hasattr(client, "search"):
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
        )

    return None
