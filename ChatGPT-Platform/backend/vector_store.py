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
        fn_clean = (filename or "").strip().lower()
        self.chunks = [
            c for c in self.chunks 
            if (c.get("filename") or "").strip().lower() != fn_clean
        ]

    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can", "cannot", "could", "did", "do",
        "does", "doing", "down", "during", "each", "few", "for", "from", "further",
        "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
        "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its",
        "itself", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off",
        "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
        "over", "own", "same", "she", "should", "so", "some", "such", "than", "that",
        "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
        "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
        "wasn't", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
        "why", "with", "would", "you", "your", "yours", "yourself", "yourselves",
        "tell", "give", "document", "file", "summarize", "summary", "overview", "explain"
    }

    DOC_INTENT_KEYWORDS = {
        "document", "documents", "file", "files", "pdf", "pdfs", "doc", "docx",
        "summarize", "summary", "overview", "content", "uploaded", "paper", "reading",
        "textbook", "notes", "attachment", "attachments", "extract", "findings"
    }

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        all_query_tokens = self._tokenize(query)
        if not all_query_tokens:
            return []

        # Prioritize informative keywords
        filtered_tokens = [t for t in all_query_tokens if t not in self.STOPWORDS and len(t) > 1]
        active_tokens = filtered_tokens if filtered_tokens else all_query_tokens

        q_counter = Counter(active_tokens)
        scored_chunks: List[Tuple[float, Dict[str, Any]]] = []

        has_explicit_doc_intent = bool(set(all_query_tokens) & self.DOC_INTENT_KEYWORDS)

        for chunk in self.chunks:
            text = chunk.get("text", "")
            chunk_tokens = self._tokenize(text)
            c_counter = Counter(chunk_tokens)
            
            # TF-IDF dot-product approximation
            intersection = set(q_counter.keys()) & set(c_counter.keys())
            score = sum(q_counter[t] * c_counter[t] for t in intersection)

            # Bonus for exact phrase / sequence match
            clean_q = query.strip().lower()
            if len(clean_q) > 3 and clean_q in text.lower():
                score += 15.0

            # Normalize by chunk length to avoid bias toward giant chunks
            norm = (len(chunk_tokens) + 12) ** 0.5
            final_score = score / norm

            # Threshold: Must have substantial match score (>= 0.22) unless explicit doc intent
            min_score = 0.10 if has_explicit_doc_intent else 0.22
            if final_score >= min_score:
                chunk_copy = dict(chunk)
                chunk_copy["score"] = round(float(final_score), 3)
                scored_chunks.append((final_score, chunk_copy))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        if scored_chunks:
            return [c for _, c in scored_chunks[:top_k]]

        # Fallback ONLY if the query explicitly asks about documents / files / summary
        if has_explicit_doc_intent:
            fallback_chunks = []
            for c in self.chunks[:top_k]:
                c_copy = dict(c)
                c_copy["score"] = 0.15
                fallback_chunks.append(c_copy)
            return fallback_chunks

        # Standard conversational / coding / math queries must NOT match document chunks
        return []

