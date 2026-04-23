"""
ChromaDB vector store for semantic search over research chunks.
Uses Ollama embeddings (nomic-embed-text).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb import Collection
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

from app.config import config

logger = logging.getLogger(__name__)

COLLECTION_NAME = "research_chunks"


class ChromaStore:
    def __init__(self):
        Path(config.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        self._embed_fn = OllamaEmbeddingFunction(
            url=f"{config.OLLAMA_BASE_URL}/api/embeddings",
            model_name=config.OLLAMA_EMBED_MODEL,
        )
        self._collection: Optional[Collection] = None

    def _get_collection(self) -> Collection:
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embed_fn,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunks(
        self,
        chunk_ids: List[str],
        chunk_texts: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Add text chunks with metadata to the vector store."""
        if not chunk_texts:
            return
        col = self._get_collection()
        # ChromaDB requires string metadata values
        clean_meta = []
        for m in metadatas:
            clean_meta.append({k: str(v) if v is not None else "" for k, v in m.items()})
        try:
            col.add(ids=chunk_ids, documents=chunk_texts, metadatas=clean_meta)
        except Exception as e:
            logger.error("ChromaDB add_chunks failed: %s", e)
            raise

    def search(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over stored chunks.
        Returns list of {id, text, score, metadata}.
        """
        col = self._get_collection()
        try:
            results = col.query(
                query_texts=[query],
                n_results=min(n_results, col.count() or 1),
                where=where or None,
                include=["documents", "distances", "metadatas"],
            )
        except Exception as e:
            logger.error("ChromaDB search failed: %s", e)
            return []

        output = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        for cid, doc, dist, meta in zip(ids, docs, dists, metas):
            output.append(
                {
                    "id": cid,
                    "text": doc,
                    "score": round(1.0 - float(dist), 4),  # cosine similarity
                    "metadata": meta,
                }
            )
        return output

    def count(self) -> int:
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def delete_by_session(self, session_id: str) -> int:
        """Delete all chunks belonging to a session. Returns deleted count."""
        col = self._get_collection()
        try:
            results = col.get(where={"session_id": session_id})
            ids = results.get("ids", [])
            if ids:
                col.delete(ids=ids)
            return len(ids)
        except Exception as e:
            logger.warning("delete_by_session failed: %s", e)
            return 0


# Module-level singleton (lazy init — Ollama may not be available at import)
_chroma: Optional[ChromaStore] = None


def get_chroma() -> ChromaStore:
    global _chroma
    if _chroma is None:
        _chroma = ChromaStore()
    return _chroma

