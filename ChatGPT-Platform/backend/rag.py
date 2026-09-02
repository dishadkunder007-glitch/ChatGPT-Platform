from typing import List, Dict, Any, Tuple
from vector_store import FastVectorStore

# In-memory per-user vector stores
user_vector_stores: Dict[int, FastVectorStore] = {}

def get_user_vector_store(user_id: int) -> FastVectorStore:
    if user_id not in user_vector_stores:
        user_vector_stores[user_id] = FastVectorStore()
    return user_vector_stores[user_id]

def build_rag_context(user_id: int, query: str, top_k: int = 3) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Returns (context_text, citations_list)
    """
    store = get_user_vector_store(user_id)
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
            "text": text[:180] + "..." if len(text) > 180 else text,
            "score": m.get("score", 0.0)
        })

    return "\n\n".join(context_parts), citations
