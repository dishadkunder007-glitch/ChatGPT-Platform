"""
LocalGPT: Retrieval-Augmented Generation (RAG) Pipeline
Full pipeline:
  Document → Extract Text → Split into Chunks → Create Embeddings → Store in FAISS
  User Question → Question Embedding → Similarity Search → Relevant Chunks → LLM → Answer

Source references include: filename, page number, chunk preview, relevance score.
"""

import os
from typing import List, Dict, Any, Tuple, Optional

try:
    from .document_loader import DocumentLoader, RecursiveCharacterChunker, DocumentChunk
    from .embeddings      import EmbeddingEngine
    from .vector_store    import FAISSVectorStore
    from .database        import LocalGPTDatabase
except (ImportError, ValueError):
    from document_loader import DocumentLoader, RecursiveCharacterChunker, DocumentChunk
    from embeddings      import EmbeddingEngine
    from vector_store    import FAISSVectorStore
    from database        import LocalGPTDatabase


class RAGPipeline:
    """
    End-to-end RAG orchestrator for LocalGPT.

    Ingestion flow:
      file_path
        └→ DocumentLoader.load_file()        # extract text + page metadata
        └→ RecursiveCharacterChunker()       # split into overlapping chunks
        └→ EmbeddingEngine.embed_documents() # dense vector embeddings
        └→ FAISSVectorStore.add_chunks()     # store in FAISS index
        └→ LocalGPTDatabase.register()      # persist metadata to SQLite

    Retrieval flow:
      user_query
        └→ EmbeddingEngine.embed_query()     # single query vector
        └→ FAISSVectorStore.similarity_search()  # top-K FAISS search
        └→ build_rag_prompt()               # inject context into prompt
        └→ get_sources_summary()            # page-level source references
    """

    def __init__(
        self,
        embedding_engine: Optional[EmbeddingEngine]  = None,
        vector_store:     Optional[FAISSVectorStore] = None,
        database:         Optional[LocalGPTDatabase] = None,
        chunk_size:   int = 500,
        chunk_overlap: int = 100
    ):
        self.embedder     = embedding_engine or EmbeddingEngine()
        self.vector_store = vector_store     or FAISSVectorStore()
        self.db           = database         or LocalGPTDatabase()
        self.loader       = DocumentLoader()
        self.chunker      = RecursiveCharacterChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """
        Full ingestion pipeline for a single file:
          Extract Text → Split into Chunks → Create Embeddings → Store in FAISS → SQLite metadata
        """
        # 1. Extract text + page metadata
        doc_data = self.loader.load_file(file_path)
        doc_id   = doc_data["doc_id"]
        filename = doc_data["filename"]
        page_cnt = doc_data.get("page_count", 1)

        # 2. Split into overlapping chunks with page attribution
        chunks = self.chunker.chunk_document(doc_data)
        if not chunks:
            return {
                "doc_id": doc_id, "filename": filename,
                "chunks_indexed": 0, "pages": page_cnt,
                "status": "empty"
            }

        # 3. Create dense embeddings
        texts      = [c.text for c in chunks]
        embeddings = self.embedder.embed_documents(texts)

        # 4. Store in FAISS
        self.vector_store.add_chunks(chunks, embeddings)

        # 5. Record in SQLite
        self.db.register_document(
            doc_id     = doc_id,
            filename   = filename,
            file_type  = doc_data["file_type"],
            file_path  = file_path,
            file_size  = doc_data["file_size"],
            chunk_count= len(chunks)
        )

        return {
            "doc_id":         doc_id,
            "filename":       filename,
            "chunks_indexed": len(chunks),
            "pages":          page_cnt,
            "file_size_bytes":doc_data["file_size"],
            "status":         "success",
            "faiss_backend":  self.vector_store._faiss_ok
        }

    def ingest_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """Ingests all supported documents in a directory recursively."""
        if not os.path.isdir(dir_path):
            return []
        results = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in DocumentLoader.SUPPORTED_EXTENSIONS:
                    fp = os.path.join(root, file)
                    try:
                        results.append(self.ingest_file(fp))
                    except Exception as e:
                        results.append({"filename": file, "status": "error", "error": str(e)})
        return results

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve_context(
        self,
        query:          str,
        top_k:          int  = 5,
        use_mmr:        bool = False,
        filter_doc_id:  Optional[str]   = None,
        score_threshold: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Pipeline: User Question → Question Embedding → FAISS Similarity Search → Relevant Chunks

        Args:
            query:           Natural language question
            top_k:           Number of chunks to retrieve
            use_mmr:         Use Maximal Marginal Relevance for diverse retrieval
            filter_doc_id:   Restrict search to a single document
            score_threshold: Minimum cosine similarity (0.0–1.0)
        """
        query_vec = self.embedder.embed_query(query)

        if use_mmr:
            return self.vector_store.max_marginal_relevance_search(
                query_vec, top_k=top_k
            )
        return self.vector_store.similarity_search(
            query_vec,
            top_k=top_k,
            filter_doc_id=filter_doc_id,
            score_threshold=score_threshold
        )

    def build_rag_prompt(
        self,
        query:           str,
        retrieved_chunks: List[Tuple[DocumentChunk, float]],
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Assembles context-injected prompt from retrieved chunks.
        Each chunk is clearly labelled with source file and page.
        """
        if not retrieved_chunks:
            return query

        context_blocks = []
        for i, (chunk, score) in enumerate(retrieved_chunks):
            fname    = chunk.metadata.get("filename",   "Document")
            page     = chunk.metadata.get("page_range", str(chunk.metadata.get("page_number", "?")))
            context_blocks.append(
                f"[Source {i+1}: {fname} | Page {page} | Relevance: {score*100:.1f}%]\n{chunk.text}"
            )

        context_str  = "\n\n---\n\n".join(context_blocks)
        instructions = custom_instructions or (
            "Answer the question accurately and concisely based strictly on the context sources below. "
            "When referencing information, mention the source file and page number. "
            "If the context does not contain enough information, state that clearly."
        )

        return (
            f"Context Sources:\n"
            f"{'='*60}\n"
            f"{context_str}\n"
            f"{'='*60}\n\n"
            f"Instructions: {instructions}\n\n"
            f"User Question: {query}\n\n"
            f"Answer:"
        )

    # ── Source References ─────────────────────────────────────────────────────

    def get_sources_summary(
        self,
        retrieved_chunks: List[Tuple[DocumentChunk, float]]
    ) -> List[Dict[str, Any]]:
        """
        Formats retrieved chunks as rich source reference cards:
          filename, page_number, page_range, similarity_score, chunk_index, preview, full_text
        """
        sources = []
        for rank, (chunk, score) in enumerate(retrieved_chunks, start=1):
            meta = chunk.metadata
            sources.append({
                "rank":             rank,
                "filename":         meta.get("filename",    "Unknown"),
                "file_type":        meta.get("file_type",   "txt"),
                "doc_id":           chunk.doc_id,
                "chunk_id":         chunk.chunk_id,
                "chunk_index":      meta.get("chunk_index",  0),
                "total_chunks":     meta.get("total_chunks", 1),
                "page_number":      meta.get("page_number",  1),
                "page_range":       meta.get("page_range",   "1"),
                "total_pages":      meta.get("total_pages",  1),
                "similarity_score": round(score * 100, 1),
                "word_count":       meta.get("word_count",   0),
                "preview":          chunk.text[:200] + ("…" if len(chunk.text) > 200 else ""),
                "full_text":        chunk.text,
            })
        return sources

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_index_stats(self) -> Dict[str, Any]:
        """Returns stats about the current vector index."""
        vs_stats = self.vector_store.get_stats()
        docs     = self.db.list_documents()
        return {
            **vs_stats,
            "indexed_documents": [
                {
                    "filename":    d["filename"],
                    "file_type":   d["file_type"],
                    "chunk_count": d["chunk_count"],
                    "doc_id":      d["doc_id"],
                }
                for d in docs
            ],
        }
