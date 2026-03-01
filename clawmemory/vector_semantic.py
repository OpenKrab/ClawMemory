from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class SemanticBackend:
    name: str = "none"

    def upsert(self, memory_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        return

    def query(self, query: str, k: int) -> dict[str, float]:
        return {}


class NoopSemanticBackend(SemanticBackend):
    name = "hashed"


class ChromaSemanticBackend(SemanticBackend):
    name = "chroma"

    def __init__(self, root: str | Path, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.root = Path(root)
        self.model_name = model_name

        import chromadb  # type: ignore
        from sentence_transformers import SentenceTransformer  # type: ignore

        self._model = SentenceTransformer(model_name)
        self._client = chromadb.PersistentClient(path=str(self.root / "chroma"))
        self._collection = self._client.get_or_create_collection(name="memories")

    def _embed(self, text: str) -> list[float]:
        vec = self._model.encode([text], normalize_embeddings=True)[0]
        return [float(v) for v in vec]

    def upsert(self, memory_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self._collection.upsert(
            ids=[memory_id],
            embeddings=[self._embed(text)],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def query(self, query: str, k: int) -> dict[str, float]:
        result = self._collection.query(
            query_embeddings=[self._embed(query)],
            n_results=max(1, k),
            include=["distances", "ids"],
        )
        ids = (result.get("ids") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        out: dict[str, float] = {}
        for mid, dist in zip(ids, dists):
            try:
                distance = float(dist)
            except (TypeError, ValueError):
                distance = 1.0
            out[str(mid)] = max(0.0, 1.0 - min(1.0, distance))
        return out


def build_semantic_backend(root: str | Path) -> SemanticBackend:
    backend = os.getenv("CLAWMEMORY_VECTOR_BACKEND", "hashed").strip().lower()
    if backend in {"", "hashed", "none", "light"}:
        return NoopSemanticBackend()

    if backend == "chroma":
        model_name = os.getenv("CLAWMEMORY_EMBED_MODEL", "all-MiniLM-L6-v2")
        try:
            return ChromaSemanticBackend(root=root, model_name=model_name)
        except Exception:
            return NoopSemanticBackend()

    return NoopSemanticBackend()
