from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from vector_store import FastVectorStore
from database import SessionLocal, DocumentChunk

# In-memory per-user vector stores cached for high-speed retrieval
user_vector_stores: Dict[int, FastVectorStore] = {}

def get_user_vector_store(user_id: int, db: Optional[Session] = None) -> FastVectorStore:
    """
    Returns the user's vector store. If not in memory, loads all persisted chunks
    from the DocumentChunk table in the database so RAG persists across restarts.
    """
    if user_id not in user_vector_stores:
        store = FastVectorStore()
        # Load from DB
        session = db or SessionLocal()
        try:
            chunks = session.query(DocumentChunk).filter(DocumentChunk.user_id == user_id).all()
            if chunks:
                chunk_dicts = [
                    {
                        "chunk_id": c.chunk_index,
                        "text": c.content,
                        "page": c.page_number,
                        "filename": c.filename,
                    }
                    for c in chunks
                ]
                store.add_chunks(chunk_dicts)
        except Exception:
            pass
        finally:
            if not db:
                session.close()

        user_vector_stores[user_id] = store

    return user_vector_stores[user_id]


def reload_user_vector_store(user_id: int, db: Optional[Session] = None) -> FastVectorStore:
    """
    Forcefully reloads the user's vector store from current persisted database chunks.
    Ensures any deleted documents are immediately and completely purged from memory.
    """
    if user_id in user_vector_stores:
        user_vector_stores[user_id].clear()
        del user_vector_stores[user_id]

    return get_user_vector_store(user_id, db=db)


def clear_user_vector_store(user_id: Optional[int] = None):
    """
    Purges in-memory vector stores. If user_id is provided, purges only that user.
    """
    if user_id is not None:
        if user_id in user_vector_stores:
            user_vector_stores[user_id].clear()
            del user_vector_stores[user_id]
    else:
        for store in list(user_vector_stores.values()):
            store.clear()
        user_vector_stores.clear()


def purge_all_vector_stores():
    """Completely flushes all vector store caches across all sessions."""
    clear_user_vector_store()


def build_rag_context(user_id: int, query: str, top_k: int = 3, db: Optional[Session] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Retrieves the most relevant document chunks for the query and returns (context_text, citations_list).
    If no documents exist for the user, returns empty context immediately.
    """
    store = get_user_vector_store(user_id, db=db)
    if not store.chunks:
        return "", []

    matches = store.search(query, top_k=top_k)
    
    if not matches:
        return "", []

    context_parts = []
    citations = []

    for i, m in enumerate(matches, 1):
        filename = m.get("filename", "document")
        page = m.get("page", 1)
        text = m.get("text", "")
        
        context_parts.append(f"[Source {i}: {filename} (Page {page})]\n{text}")
        citations.append({
            "citation_id": i,
            "filename": filename,
            "page": page,
            "chunk_id": m.get("chunk_id", 0),
            "text": text[:200] + "..." if len(text) > 200 else text,
            "score": m.get("score", 0.0)
        })

    return "\n\n".join(context_parts), citations


