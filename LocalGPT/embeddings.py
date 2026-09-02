"""
LocalGPT: Dense Vector Embedding Engine
Computes dense semantic embeddings for text chunks and search queries using
SentenceTransformers, PyTorch HuggingFace models, or a fast offline fallback.
"""

from typing import List, Union, Optional
import numpy as np
import torch
import torch.nn.functional as F


class EmbeddingEngine:
    """
    Manages vector embedding generation with multiple backends and graceful offline fallbacks.
    """

    SUPPORTED_MODELS = [
        "sentence-transformers/all-MiniLM-L6-v2",
        "BAAI/bge-small-en-v1.5",
        "intfloat/e5-small-v2"
    ]

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.st_model = None
        self.hf_model = None
        self.hf_tokenizer = None
        self.dimension = 384
        self.is_fallback = False
        self._init_model()

    def _init_model(self):
        """Attempts to load sentence-transformers or huggingface transformers with fallback."""
        # 1. Try SentenceTransformers
        try:
            from sentence_transformers import SentenceTransformer
            print(f"[EmbeddingEngine] Loading SentenceTransformer: '{self.model_name}' on {self.device}...")
            self.st_model = SentenceTransformer(self.model_name, device=self.device)
            self.dimension = self.st_model.get_sentence_embedding_dimension()
            self.is_fallback = False
            print(f"[EmbeddingEngine] Loaded successfully. Dimension: {self.dimension}")
            return
        except Exception as e:
            print(f"[EmbeddingEngine] Note: SentenceTransformer load bypassed ({e}). Trying HuggingFace AutoModel...")

        # 2. Try HuggingFace AutoModel with mean pooling
        try:
            from transformers import AutoTokenizer, AutoModel
            self.hf_tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.hf_model = AutoModel.from_pretrained(self.model_name).to(self.device)
            self.hf_model.eval()
            self.dimension = getattr(self.hf_model.config, "hidden_size", 384)
            self.is_fallback = False
            print(f"[EmbeddingEngine] HF AutoModel loaded successfully. Dimension: {self.dimension}")
            return
        except Exception as e:
            print(f"[EmbeddingEngine] Warning: HuggingFace model load failed ({e}). Initializing offline fallback embedding engine.")

        # 3. Offline dense semantic hashing fallback
        self.is_fallback = True
        self.dimension = 384

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a list of text strings into an [N, dimension] normalized numpy array.
        """
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        # Non-empty sanity
        safe_texts = [t if t.strip() else " " for t in texts]

        if self.st_model is not None:
            embeddings = self.st_model.encode(
                safe_texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embeddings.astype(np.float32)

        if self.hf_model is not None and self.hf_tokenizer is not None:
            return self._hf_mean_pooling(safe_texts)

        return self._fallback_embed(safe_texts)

    def embed_query(self, text: str) -> np.ndarray:
        """
        Embeds a single query string into a 1D [dimension] normalized vector.
        """
        result = self.embed_documents([text])
        return result[0]

    @torch.no_grad()
    def _hf_mean_pooling(self, texts: List[str]) -> np.ndarray:
        encoded = self.hf_tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)

        outputs = self.hf_model(**encoded)
        token_embeddings = outputs.last_hidden_state  # [batch, seq_len, dim]
        input_mask_expanded = encoded["attention_mask"].unsqueeze(-1).expand(token_embeddings.size()).float()
        
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        mean_pooled = sum_embeddings / sum_mask
        
        # Normalize
        normalized = F.normalize(mean_pooled, p=2, dim=1).cpu().numpy()
        return normalized.astype(np.float32)

    def _fallback_embed(self, texts: List[str]) -> np.ndarray:
        """
        Deterministic, lightweight token-distribution dense embedding fallback.
        Ensures zero runtime crashes in air-gapped environments without HuggingFace weights.
        """
        embeddings = []
        for text in texts:
            vec = np.zeros(self.dimension, dtype=np.float32)
            words = text.lower().split()
            if not words:
                words = ["empty"]
            for i, w in enumerate(words):
                # Hash word into vector components with positional weighting
                h = abs(hash(w))
                idx1 = h % self.dimension
                idx2 = (h >> 5) % self.dimension
                idx3 = (h >> 11) % self.dimension
                weight = 1.0 / (1.0 + 0.05 * i)
                vec[idx1] += weight
                vec[idx2] -= weight * 0.5
                vec[idx3] += weight * 0.25

            # L2 normalize
            norm = np.linalg.norm(vec)
            if norm > 1e-9:
                vec = vec / norm
            embeddings.append(vec)

        return np.array(embeddings, dtype=np.float32)

    @staticmethod
    def cosine_similarity(query_vec: np.ndarray, doc_matrix: np.ndarray) -> np.ndarray:
        """
        Computes cosine similarities between a 1D query vector and an [N, dim] matrix of document vectors.
        """
        if doc_matrix.ndim == 1:
            doc_matrix = np.expand_dims(doc_matrix, 0)
        
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 1e-9:
            q_normed = query_vec / q_norm
        else:
            q_normed = query_vec

        doc_norms = np.linalg.norm(doc_matrix, axis=1, keepdims=True)
        doc_norms = np.where(doc_norms > 1e-9, doc_norms, 1.0)
        doc_normed = doc_matrix / doc_norms

        similarities = np.dot(doc_normed, q_normed)
        return similarities
