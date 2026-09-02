import os
import math
import re
from typing import List, Dict, Any, Tuple
from collections import Counter

class FastVectorStore:
    """
    In-memory vector store with TF-IDF / BM25-style cosine similarity & sub-string ranking.
    Fast, zero external model load time, ultra responsive on any hosted server.
    """
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []

    def clear(self):
        self.chunks = []

    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        self.chunks.extend(new_chunks)

    def remove_document(self, filename: str):
        self.chunks = [c for c in self.chunks if c.get("filename") != filename]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.chunks[:top_k]

        q_counter = Counter(query_tokens)
        scored_chunks: List[Tuple[float, Dict[str, Any]]] = []

        for chunk in self.chunks:
            text = chunk.get("text", "")
            chunk_tokens = self._tokenize(text)
            c_counter = Counter(chunk_tokens)
            
            # Simple TF-IDF dot-product approximation
            intersection = set(q_counter.keys()) & set(c_counter.keys())
            score = sum(q_counter[t] * c_counter[t] for t in intersection)

            # Bonus for exact sequence matches
            if query.lower() in text.lower():
                score += 10.0

            # Normalize by chunk length to avoid bias
            norm = (len(chunk_tokens) + 10) ** 0.5
            final_score = score / norm

            if final_score > 0.05:
                chunk_copy = dict(chunk)
                chunk_copy["score"] = round(float(final_score), 3)
                scored_chunks.append((final_score, chunk_copy))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_chunks[:top_k]]
