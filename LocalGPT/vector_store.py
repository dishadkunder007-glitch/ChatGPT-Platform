"""
LocalGPT: FAISS-Backed Vector Store
Full pipeline:
  Document → Extract Text → Split Chunks → Create Embeddings → Store in FAISS
  User Query → Question Embedding → FAISS Similarity Search → Relevant Chunks

Uses FAISS IndexFlatIP (inner product on L2-normalised vectors = cosine similarity).
Falls back to numpy cosine search if faiss-cpu is not available.
"""

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

try:
    from .document_loader import DocumentChunk
    from .embeddings import EmbeddingEngine
except (ImportError, ValueError):
    from document_loader import DocumentChunk
    from embeddings import EmbeddingEngine


class FAISSVectorStore:
    """
    FAISS-powered vector index for fast semantic chunk retrieval.
    Stores embeddings in a FAISS IndexFlatIP index and persists chunk
    metadata to disk as JSON + pickle.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            base  = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(base, "data", "faiss_index")
        os.makedirs(storage_dir, exist_ok=True)

        self.storage_dir  = storage_dir
        self.index_path   = os.path.join(storage_dir, "index.faiss")
        self.chunks_path  = os.path.join(storage_dir, "chunks.json")

        self.chunks:      List[DocumentChunk] = []
        self.faiss_index  = None           # faiss.Index
        self.dimension    = 0
        self._faiss_ok    = self._check_faiss()

        self.load()

    # ── FAISS availability ────────────────────────────────────────────────────

    @staticmethod
    def _check_faiss() -> bool:
        try:
            import faiss  # noqa
            return True
        except ImportError:
            print("[VectorStore] faiss-cpu not available — using numpy cosine fallback.")
            return False

    # ── Build / add ───────────────────────────────────────────────────────────

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """
        Adds document chunks and their dense embeddings to the FAISS index.
        Embeddings must be L2-normalised float32 arrays of shape (N, dim).
        """
        if not chunks or embeddings.shape[0] == 0:
            return
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {embeddings.shape[0]} embeddings.")

        embs = embeddings.astype(np.float32)
        dim  = embs.shape[1]

        if self._faiss_ok:
            import faiss
            # Normalise for cosine similarity via inner product
            faiss.normalize_L2(embs)

            if self.faiss_index is None or self.dimension != dim:
                self.dimension   = dim
                self.faiss_index = faiss.IndexFlatIP(dim)

            self.faiss_index.add(embs)
        else:
            # Numpy fallback: keep a raw matrix
            if self.faiss_index is None:
                self.faiss_index = embs
                self.dimension   = dim
            else:
                self.faiss_index = np.vstack([self.faiss_index, embs])

        self.chunks.extend(chunks)
        self.save()

    # ── Search ────────────────────────────────────────────────────────────────

    def similarity_search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter_doc_id: Optional[str] = None,
        score_threshold: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        FAISS cosine similarity search.
        Returns list of (DocumentChunk, score) sorted by relevance descending.

        Pipeline:
          User Question → Question Embedding → Similarity Search → Relevant Chunks
        """
        if not self.chunks or self.faiss_index is None:
            return []

        q = query_embedding.astype(np.float32)

        if self._faiss_ok:
            import faiss
            q_norm = q.copy().reshape(1, -1)
            faiss.normalize_L2(q_norm)

            if filter_doc_id:
                # Search broader pool, then post-filter by doc_id
                k = min(len(self.chunks), top_k * 10)
                scores_arr, idx_arr = self.faiss_index.search(q_norm, k)
                results = []
                for score, idx in zip(scores_arr[0], idx_arr[0]):
                    if idx < 0:
                        continue
                    chunk = self.chunks[idx]
                    if chunk.doc_id == filter_doc_id and float(score) >= score_threshold:
                        results.append((chunk, float(score)))
                        if len(results) >= top_k:
                            break
                return results
            else:
                k = min(len(self.chunks), top_k)
                scores_arr, idx_arr = self.faiss_index.search(q_norm, k)
                results = []
                for score, idx in zip(scores_arr[0], idx_arr[0]):
                    if idx >= 0 and float(score) >= score_threshold:
                        results.append((self.chunks[idx], float(score)))
                return results

        else:
            # Numpy cosine fallback
            scores = EmbeddingEngine.cosine_similarity(q, self.faiss_index)
            if filter_doc_id:
                mask = np.array([1.0 if c.doc_id == filter_doc_id else 0.0 for c in self.chunks])
                scores = scores * mask
            top_indices = np.argsort(scores)[::-1][:top_k]
            return [
                (self.chunks[i], float(scores[i]))
                for i in top_indices
                if float(scores[i]) >= score_threshold
            ]

    def max_marginal_relevance_search(
        self,
        query_embedding: np.ndarray,
        top_k:      int   = 5,
        fetch_k:    int   = 25,
        lambda_mult: float = 0.5
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        MMR search: balances relevance vs. diversity to avoid redundant chunks.
        """
        if not self.chunks or self.faiss_index is None:
            return []

        # 1. Fetch a larger candidate pool first
        candidates = self.similarity_search(query_embedding, top_k=fetch_k)
        if not candidates:
            return []

        # 2. Extract candidate embeddings
        q = query_embedding.astype(np.float32)
        cand_chunks  = [c for c, _ in candidates]
        cand_scores  = np.array([s for _, s in candidates], dtype=np.float32)

        # Rebuild embedding matrix for MMR
        cand_embs = np.vstack([
            self._get_embedding_for_chunk(c) for c in cand_chunks
        ])

        selected_idx:    List[int]   = []
        remaining_idx:   List[int]   = list(range(len(cand_chunks)))

        while len(selected_idx) < top_k and remaining_idx:
            best_mmr = -float("inf")
            best_i   = None

            for i in remaining_idx:
                sim_q = float(cand_scores[i])
                if not selected_idx:
                    mmr = sim_q
                else:
                    sel_embs  = cand_embs[selected_idx]
                    sim_sel   = float(np.max(EmbeddingEngine.cosine_similarity(
                        cand_embs[i], sel_embs
                    )))
                    mmr = lambda_mult * sim_q - (1 - lambda_mult) * sim_sel

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_i   = i

            if best_i is not None:
                selected_idx.append(best_i)
                remaining_idx.remove(best_i)
            else:
                break

        return [(cand_chunks[i], float(cand_scores[i])) for i in selected_idx]

    def _get_embedding_for_chunk(self, chunk: DocumentChunk) -> np.ndarray:
        """Retrieves embedding vector for a chunk by its position in self.chunks."""
        try:
            idx = self.chunks.index(chunk)
            if self._faiss_ok:
                import faiss
                emb = np.zeros((1, self.dimension), dtype=np.float32)
                self.faiss_index.reconstruct(idx, emb[0])
                return emb[0]
            else:
                return self.faiss_index[idx]
        except Exception:
            return np.zeros(self.dimension, dtype=np.float32)

    # ── Delete / clear ────────────────────────────────────────────────────────

    def delete_document(self, doc_id: str):
        """Removes all chunks for a document. Rebuilds FAISS index from scratch."""
        keep = [i for i, c in enumerate(self.chunks) if c.doc_id != doc_id]
        if len(keep) == len(self.chunks):
            return  # nothing to remove

        if self._faiss_ok and self.faiss_index is not None:
            import faiss
            # Collect surviving embeddings
            kept_embs = np.zeros((len(keep), self.dimension), dtype=np.float32)
            for new_i, old_i in enumerate(keep):
                self.faiss_index.reconstruct(old_i, kept_embs[new_i])

            # Rebuild index
            self.faiss_index = faiss.IndexFlatIP(self.dimension) if keep else None
            if kept_embs.shape[0] > 0:
                self.faiss_index.add(kept_embs)
        elif self.faiss_index is not None:
            self.faiss_index = (
                self.faiss_index[keep] if len(keep) > 0 else None
            )

        self.chunks = [self.chunks[i] for i in keep]
        self.save()

    def clear(self):
        """Wipes entire index from memory and disk."""
        self.chunks      = []
        self.faiss_index = None
        self.dimension   = 0
        for p in [self.index_path, self.chunks_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self):
        """Saves FAISS index + chunk metadata to disk."""
        try:
            chunks_data = [c.to_dict() for c in self.chunks]
            with open(self.chunks_path, "w", encoding="utf-8") as f:
                json.dump(chunks_data, f, indent=2)

            if self._faiss_ok and self.faiss_index is not None:
                import faiss
                faiss.write_index(self.faiss_index, self.index_path)
            elif self.faiss_index is not None:
                np.save(self.index_path + ".npy", self.faiss_index)
        except Exception as e:
            print(f"[VectorStore] Warning: Failed to save ({e})")

    def load(self):
        """Loads FAISS index + chunk metadata from disk."""
        if os.path.exists(self.chunks_path):
            try:
                with open(self.chunks_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.chunks = [
                    DocumentChunk(
                        chunk_id    = c["chunk_id"],
                        doc_id      = c["doc_id"],
                        text        = c["text"],
                        chunk_index = c["chunk_index"],
                        metadata    = c.get("metadata", {})
                    )
                    for c in raw
                ]
            except Exception as e:
                print(f"[VectorStore] Warning: Could not load chunks ({e})")

        if self._faiss_ok:
            if os.path.exists(self.index_path):
                try:
                    import faiss
                    self.faiss_index = faiss.read_index(self.index_path)
                    self.dimension   = self.faiss_index.d
                except Exception as e:
                    print(f"[VectorStore] Warning: Could not load FAISS index ({e})")
        else:
            npy_path = self.index_path + ".npy"
            if os.path.exists(npy_path):
                try:
                    self.faiss_index = np.load(npy_path)
                    self.dimension   = self.faiss_index.shape[1]
                except Exception as e:
                    print(f"[VectorStore] Warning: Could not load numpy index ({e})")

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        unique_docs = set(c.doc_id for c in self.chunks)
        return {
            "total_chunks":    len(self.chunks),
            "total_documents": len(unique_docs),
            "embedding_dim":   self.dimension,
            "faiss_backend":   self._faiss_ok,
            "index_size":      (
                os.path.getsize(self.index_path) if os.path.exists(self.index_path) else 0
            ),
            "is_empty": len(self.chunks) == 0,
        }


# ── Backwards-compatible alias (old code may reference VectorStore) ───────────
VectorStore = FAISSVectorStore
