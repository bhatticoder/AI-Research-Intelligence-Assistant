"""
Embedding Service - Sentence Transformers + ChromaDB vector operations.
"""

import logging
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Handles document embeddings via Ollama and ChromaDB vector storage."""

    def __init__(self):
        self._chroma_client = None
        self._collection_name = "aria_documents"

    @property
    def chroma_client(self):
        if self._chroma_client is None:
            try:
                client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                client.heartbeat()
                self._chroma_client = client
                logger.info(f"Connected to ChromaDB server at {settings.chroma_host}:{settings.chroma_port}")
            except Exception as e:
                logger.warning(f"Could not connect to ChromaDB server at {settings.chroma_host}:{settings.chroma_port} ({e}). Falling back to local PersistentClient.")
                self._chroma_client = chromadb.PersistentClient(
                    path="./chroma_db",
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
        return self._chroma_client

    def get_or_create_collection(self, name: Optional[str] = None):
        """Get or create a ChromaDB collection with fallback recovery.

        Handles the ``KeyError: '_type'`` failure that occurs when a DB written by
        an older chromadb (which stored ``config_json_str='{}'``) is opened by a
        newer chromadb whose ``from_json()`` requires a ``_type`` key. Every client
        read (get/create/get_or_create) routes through the same internal collections
        read, so the only recovery that works — and that preserves already-embedded
        vectors — is to repair the corrupt config row in-place, then retry.
        """
        collection_name = name or self._collection_name
        try:
            return self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            if self._is_config_migration_error(e):
                logger.warning(
                    f"ChromaDB config migration error ({type(e).__name__}: {e}). "
                    "Repairing collection config in-place (vectors preserved)..."
                )
                if self._repair_chroma_config(space="cosine"):
                    # Reset the client so it re-reads the repaired sysdb rows.
                    self._chroma_client = None
                    return self.chroma_client.get_or_create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"},
                    )

            logger.warning(f"get_or_create_collection failed ({e}). Attempting recovery...")
            try:
                return self.chroma_client.get_collection(name=collection_name)
            except Exception:
                # Last resort: recreate. Reached only when the config error could not
                # be repaired (e.g. remote HttpClient with no local sqlite file).
                try:
                    self.chroma_client.delete_collection(name=collection_name)
                except Exception:
                    pass
                return self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )

    @staticmethod
    def _is_config_migration_error(exc: Exception) -> bool:
        """True when the exception is the chromadb config-version migration failure."""
        if isinstance(exc, KeyError) and "_type" in str(exc):
            return True
        text = f"{type(exc).__name__}: {exc}".lower()
        return "_type" in text or ("configuration" in text and "json" in text)

    def _repair_chroma_config(self, space: str = "cosine") -> bool:
        """Repair ``collections.config_json_str`` rows missing the ``_type`` key.

        Rewrites only rows whose stored config cannot be parsed by the running
        chromadb, injecting a valid default config. Embedded vectors, metadata, and
        the HNSW index are untouched. Only works for a local PersistentClient (there
        is a sqlite file to repair); returns False for a remote HttpClient.
        """
        import os
        import glob
        import sqlite3
        import json

        db_paths = glob.glob(os.path.join("./chroma_db", "**", "chroma.sqlite3"), recursive=True)
        db_paths += glob.glob(os.path.join("./chroma_db", "chroma.sqlite3"))
        db_paths = sorted(set(db_paths))
        if not db_paths:
            logger.warning("No local chroma.sqlite3 found to repair (remote client?).")
            return False

        valid_config = {
            "hnsw_configuration": {
                "space": space,
                "ef_construction": 100,
                "ef_search": 10,
                "num_threads": 4,
                "M": 16,
                "resize_factor": 1.2,
                "batch_size": 100,
                "sync_threshold": 1000,
                "_type": "HNSWConfigurationInternal",
            },
            "_type": "CollectionConfigurationInternal",
        }
        config_str = json.dumps(valid_config)

        repaired = 0
        for path in db_paths:
            conn = sqlite3.connect(path)
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(collections)").fetchall()]
                if "config_json_str" not in cols:
                    continue
                for cid, cfg in conn.execute("SELECT id, config_json_str FROM collections").fetchall():
                    needs_fix = False
                    try:
                        parsed = json.loads(cfg) if cfg else {}
                        if "_type" not in parsed:
                            needs_fix = True
                    except (TypeError, json.JSONDecodeError):
                        needs_fix = True
                    if needs_fix:
                        conn.execute(
                            "UPDATE collections SET config_json_str = ? WHERE id = ?",
                            (config_str, cid),
                        )
                        repaired += 1
                conn.commit()
            except Exception as e:
                logger.error(f"Failed repairing ChromaDB config in {path}: {e}")
            finally:
                conn.close()

        if repaired:
            logger.warning(f"Repaired {repaired} ChromaDB collection config row(s) missing '_type'.")
        return repaired > 0

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts using Ollama."""
        import ollama as ollama_lib
        client = ollama_lib.AsyncClient(host=settings.ollama_base_url)

        embeddings = []
        # Batch in groups of 32 for efficiency
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                try:
                    response = await client.embed(
                        model=settings.ollama_embed_model,
                        input=text,
                    )
                    vecs = getattr(response, "embeddings", None) or (response.get("embeddings") if isinstance(response, dict) else None)
                    if vecs:
                        embeddings.append(vecs[0])
                    else:
                        embeddings.append(response["embeddings"][0])
                except Exception as e:
                    logger.error(f"Embedding error: {e}")
                    # Return zero vector as fallback
                    embeddings.append([0.0] * 768)

        return embeddings

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        result = await self.embed_texts([text])
        return result[0]

    # ── ChromaDB Operations ───────────────────────────────────────

    async def add_documents(
        self,
        doc_id: str,
        chunks: list[str],
        metadatas: Optional[list[dict]] = None,
        collection_name: Optional[str] = None,
    ) -> int:
        """Embed and store document chunks in ChromaDB."""
        if not chunks:
            return 0

        collection = self.get_or_create_collection(collection_name)

        # Generate embeddings
        embeddings = await self.embed_texts(chunks)

        # Prepare IDs and metadata
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        clean_metadatas = []
        for i in range(len(chunks)):
            base_meta = metadatas[i] if (metadatas and i < len(metadatas)) else (metadatas[0] if metadatas else {})
            clean_meta = {str(k): str(v) for k, v in base_meta.items()}
            clean_meta["document_id"] = str(doc_id)
            clean_meta["chunk_index"] = str(i)
            clean_metadatas.append(clean_meta)

        # Upsert into ChromaDB
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=clean_metadatas,
        )

        logger.info(f"Stored {len(chunks)} chunks for document {doc_id}")
        return len(chunks)

    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        collection_name: Optional[str] = None,
        where: Optional[dict] = None,
    ) -> dict:
        """Query ChromaDB for similar documents."""
        collection = self.get_or_create_collection(collection_name)

        # Embed the query
        query_embedding = await self.embed_single(query_text)

        # Search
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        return {
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        }

    async def delete_document(self, doc_id: str, collection_name: Optional[str] = None):
        """Delete all chunks for a document from ChromaDB."""
        collection = self.get_or_create_collection(collection_name)
        try:
            collection.delete(where={"document_id": doc_id})
            logger.info(f"Deleted embeddings for document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings for {doc_id}: {e}")

    async def get_stats(self, collection_name: Optional[str] = None) -> dict:
        """Get collection statistics."""
        try:
            collection = self.get_or_create_collection(collection_name)
            return {
                "total_chunks": collection.count(),
                "collection_name": collection.name,
            }
        except Exception as e:
            return {"error": str(e)}
