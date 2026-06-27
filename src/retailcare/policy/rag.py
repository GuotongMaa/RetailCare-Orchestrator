"""Policy RAG over Chroma (M2). Versioned citations preserved in metadata.

Uses Chroma's built-in ONNX MiniLM embedding (no torch / no API needed). Falls
back to the deterministic lexical search in `store.py` if Chroma is unavailable,
so the pipeline never hard-blocks on the vector layer (manual §8.3).
"""
from __future__ import annotations

import os

from retailcare.config import settings
from retailcare.policy import store
from retailcare.tools.schema import PolicyChunk

_COLLECTION = None
_BACKEND = "uninitialized"


def _build():
    global _COLLECTION, _BACKEND
    try:
        import chromadb

        host = os.getenv("CHROMA_HOST")
        if host:
            client = chromadb.HttpClient(host=host, port=int(os.getenv("CHROMA_PORT", "8000")))
            backend = f"chroma-http:{host}:{os.getenv('CHROMA_PORT', '8000')}"
        else:
            client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
            backend = "chroma-persistent"
        col = client.get_or_create_collection("policy", metadata={"hnsw:space": "cosine"})
        col.upsert(
            ids=[c.chunk_id for c in store._CHUNKS],
            documents=[c.text for c in store._CHUNKS],
            metadatas=[{"version": c.version} for c in store._CHUNKS],
        )
        _COLLECTION, _BACKEND = col, backend
    except Exception:  # noqa: BLE001 - any chroma/onnx failure -> lexical fallback
        _COLLECTION, _BACKEND = None, "lexical"


def backend() -> str:
    if _BACKEND == "uninitialized":
        _build()
    return _BACKEND


def search(query: str, k: int = 3) -> list[PolicyChunk]:
    if _BACKEND == "uninitialized":
        _build()
    if _COLLECTION is None:
        return store.search(query, k=k)
    res = _COLLECTION.query(query_texts=[query], n_results=k)
    ids = res["ids"][0]
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res.get("distances", [[0.0] * len(ids)])[0]
    return [
        PolicyChunk(chunk_id=i, text=d, version=m.get("version", store.POLICY_VERSION),
                    score=round(1.0 - float(dist), 4))
        for i, d, m, dist in zip(ids, docs, metas, dists, strict=False)
    ]
