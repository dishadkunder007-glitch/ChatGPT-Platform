"""
LocalGPT: Mechanistic Interpretability & X-Ray Engine
Exposes the full internal pipeline of a transformer:
  Tokens → Token IDs → Embeddings → Transformer Layers →
  Attention → Hidden States → Logits → Probabilities → Generated Tokens
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import plotly.graph_objects as go

try:
    from .model import XRayModel
    from .visualization import (
        plot_attention_heatmap,
        plot_multi_head_grid,
        plot_attention_rollout,
        plot_logit_lens_matrix,
        plot_residual_stream_dynamics,
        plot_top_logits_bar,
        plot_generation_timeline,
        plot_neuron_sparsity,
        plot_embedding_pca_2d,
        plot_hidden_state_pca,
        plot_top_logits_probabilities,
        generate_ascii_attention_matrix,
        generate_token_probability_bars,
        render_token_probability_html,
        DARK_LAYOUT
    )
except (ImportError, ValueError):
    from model import XRayModel
    from visualization import (
        plot_attention_heatmap,
        plot_multi_head_grid,
        plot_attention_rollout,
        plot_logit_lens_matrix,
        plot_residual_stream_dynamics,
        plot_top_logits_bar,
        plot_generation_timeline,
        plot_neuron_sparsity,
        plot_embedding_pca_2d,
        plot_hidden_state_pca,
        plot_top_logits_probabilities,
        generate_ascii_attention_matrix,
        generate_token_probability_bars,
        render_token_probability_html,
        DARK_LAYOUT
    )


class XRayEngine:
    """
    High-level X-Ray orchestrator.
    Provides both targeted single-figure generators and a full
    deep inspection that collects every internal stage at once.
    """

    def __init__(self, model: Optional[XRayModel] = None):
        self.model = model or XRayModel()

    # ── Full inspection ─────────────────────────────────────────────

    def run_deep_inspection(self, prompt: str, top_k: int = 5) -> Dict[str, Any]:
        """Runs a complete forward pass and returns all raw activations."""
        return self.model.inspect(prompt, top_k=top_k)

    def get_full_xray_data(self, prompt: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Returns a unified dict with every internal stage, ready for the UI:
          tokens, token_ids, embeddings, hidden_states, attentions,
          logit_lens, residual_dynamics, top_logits, mlp_summary, ascii_attn
        """
        # 1. Tokenise
        tok_data = self.model.tokenizer.tokenize(prompt)
        tokens   = tok_data.get("clean_tokens", [])
        ids      = tok_data.get("token_ids", [])

        # 2. Embeddings
        try:
            emb_data   = self.model.get_input_embeddings(ids)
            embeddings = emb_data.get("embeddings")          # [seq, dim]
        except Exception:
            embeddings = None

        # 3. Full model inspection
        insp = self.model.inspect(prompt, top_k=top_k) or {}

        # 4. Top logit tokens + probs (last position)
        top_tokens = []
        top_probs  = []
        if "top_candidates" in insp and insp["top_candidates"]:
            for tok_str, prob in insp["top_candidates"][:top_k]:
                top_tokens.append(tok_str)
                top_probs.append(float(prob))

        # 5. ASCII attention for the first head
        ascii_attn = ""
        if "attentions" in insp and insp["attentions"] is not None:
            try:
                mat = insp["attentions"][0, 0]   # Layer 0, Head 0
                ascii_attn = generate_ascii_attention_matrix(tokens, mat)
            except Exception:
                pass

        # 6. Next Token Probability Views (ASCII and HTML)
        ascii_prob_bars = generate_token_probability_bars(top_tokens, top_probs)
        html_prob_bars  = render_token_probability_html(top_tokens, top_probs)

        # 7. Per-token embedding stats table
        emb_stats = []
        if embeddings is not None:
            for i, tok in enumerate(tokens):
                v = embeddings[i]
                emb_stats.append({
                    "Token":      tok,
                    "Token ID":   ids[i] if i < len(ids) else "?",
                    "Emb Dim":    int(v.shape[0]),
                    "L2 Norm":    round(float(np.linalg.norm(v)), 4),
                    "Mean":       round(float(np.mean(v)),         4),
                    "Std":        round(float(np.std(v)),          4),
                    "Min":        round(float(np.min(v)),          4),
                    "Max":        round(float(np.max(v)),          4),
                })

        num_layers = 0
        num_heads = 0
        if insp.get("attentions") is not None and len(insp["attentions"].shape) >= 2:
            num_layers = int(insp["attentions"].shape[0])
            num_heads = int(insp["attentions"].shape[1])

        # 8. Step-by-step Autoregressive Generation History
        gen_history = []
        try:
            if hasattr(self.model, "generate_step_by_step"):
                gen_history = self.model.generate_step_by_step(prompt, max_new_tokens=8, top_k=top_k)
        except Exception:
            gen_history = []

        return {
            # Raw data
            "tokens":           tokens,
            "token_ids":        ids,
            "embeddings":       embeddings,
            "emb_stats":        emb_stats,
            "attentions":       insp.get("attentions"),
            "hidden_states":    insp.get("hidden_states"),
            "logit_lens":       insp.get("logit_lens"),
            "residual_dynamics":insp.get("residual_dynamics"),
            "mlp_summary":      insp.get("mlp_summary"),
            "rollout_matrix":   insp.get("rollout_matrix"),
            "top_tokens":       top_tokens,
            "top_probs":        top_probs,
            "top_candidates":   insp.get("top_candidates", []),
            "ascii_attn":       ascii_attn,
            "ascii_prob_bars":  ascii_prob_bars,
            "html_prob_bars":   html_prob_bars,
            "generation_history": gen_history,
            # Meta
            "num_layers":       num_layers,
            "num_heads":        num_heads,
        }

    # ── Targeted figure generators ────────────────────────────────────────────

    def generate_attention_heatmap(
        self, prompt: str, layer: int = 1, head: int = 1
    ) -> Optional[go.Figure]:
        data = self.model.inspect(prompt)
        if not data or "attentions" not in data or data["attentions"] is None:
            return None
        attns = data["attentions"]
        l_idx = max(0, min(layer - 1, attns.shape[0] - 1))
        h_idx = max(0, min(head  - 1, attns.shape[1] - 1))
        mat   = attns[l_idx, h_idx]
        return plot_attention_heatmap(data["clean_tokens"], mat, l_idx + 1, h_idx + 1)

    def generate_multi_head_grid(
        self, prompt: str, layer: int = 1
    ) -> Optional[go.Figure]:
        data = self.model.inspect(prompt)
        if not data or "attentions" not in data or data["attentions"] is None:
            return None
        attns = data["attentions"]
        l_idx = max(0, min(layer - 1, attns.shape[0] - 1))
        return plot_multi_head_grid(data["clean_tokens"], attns[l_idx], l_idx + 1)

    def generate_attention_rollout(self, prompt: str) -> Optional[go.Figure]:
        data = self.model.inspect(prompt)
        if not data or "rollout_matrix" not in data or data["rollout_matrix"] is None:
            return None
        return plot_attention_rollout(data["clean_tokens"], data["rollout_matrix"])

    def generate_logit_lens(self, prompt: str, top_k: int = 5) -> Optional[go.Figure]:
        data = self.model.inspect(prompt, top_k=top_k)
        if not data or "logit_lens" not in data or data["logit_lens"] is None:
            return None
        return plot_logit_lens_matrix(data["clean_tokens"], data["logit_lens"])

    def generate_residual_dynamics(
        self, prompt: str
    ) -> Tuple[Optional[go.Figure], Optional[go.Figure]]:
        data = self.model.inspect(prompt)
        if not data or "residual_dynamics" not in data or data["residual_dynamics"] is None:
            return None, None
        return plot_residual_stream_dynamics(data["residual_dynamics"], data["clean_tokens"])

    def generate_neuron_sparsity(self, prompt: str) -> Optional[go.Figure]:
        data = self.model.inspect(prompt)
        if not data or "mlp_summary" not in data or data["mlp_summary"] is None:
            return None
        return plot_neuron_sparsity(data["mlp_summary"])

    def generate_embedding_pca(self, prompt: str) -> Optional[go.Figure]:
        tok_data = self.model.tokenizer.tokenize(prompt)
        emb_data = self.model.get_input_embeddings(tok_data["token_ids"])
        if "embeddings" not in emb_data or emb_data["embeddings"] is None:
            return None
        return plot_embedding_pca_2d(
            tok_data["clean_tokens"],
            tok_data["token_ids"],
            emb_data["embeddings"]
        )

    def generate_hidden_state_pca(
        self, prompt: str, layer_idx: int = -1
    ) -> Optional[go.Figure]:
        data = self.model.inspect(prompt)
        if not data or "hidden_states" not in data or data["hidden_states"] is None:
            return None
        hs = data["hidden_states"]   # [num_layers, seq, d_model]
        l  = max(0, min(layer_idx, hs.shape[0] - 1))
        return plot_hidden_state_pca(
            data["clean_tokens"], hs[l],
            layer_label=f"Layer {l + 1}"
        )

    def generate_top_logits(
        self, prompt: str, top_k: int = 10
    ) -> Optional[go.Figure]:
        data = self.model.inspect(prompt, top_k=top_k)
        if not data or "top_candidates" not in data or not data["top_candidates"]:
            return None
        toks  = [c[0] for c in data["top_candidates"][:top_k]]
        probs = [c[1] for c in data["top_candidates"][:top_k]]
        return plot_top_logits_probabilities(toks, probs, top_k=top_k)

    def generate_generation_timeline(
        self, prompt: str, max_new_tokens: int = 8
    ) -> Optional[go.Figure]:
        if not hasattr(self.model, "generate_step_by_step"):
            return None
        history = self.model.generate_step_by_step(prompt, max_new_tokens=max_new_tokens)
        if not history:
            return None
        return plot_generation_timeline(history)

