"""
LLM-XRay: Model & Mechanistic Interpretability Engine
Extracts multi-head attention, hidden states, logit lens unembeddings,
residual stream dynamics, and MLP activations via PyTorch forward hooks.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from .tokenizer import XRayTokenizer
    from .semantic_responder import generate_dynamic_response
except (ImportError, ValueError):
    from tokenizer import XRayTokenizer
    from semantic_responder import generate_dynamic_response



class SyntheticToyTransformer(nn.Module):
    """
    A lightweight, fully functional self-contained Transformer used as a fallback
    when downloading large pre-trained weights is not possible.
    """
    def __init__(self, vocab_size=50257, d_model=128, n_heads=4, n_layers=4):
        super().__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers

        self.wte = nn.Embedding(vocab_size, d_model)
        self.wpe = nn.Embedding(1024, d_model)
        
        self.layers = nn.ModuleList([
            nn.ModuleDict({
                "ln_1": nn.LayerNorm(d_model),
                "attn": nn.MultiheadAttention(d_model, n_heads, batch_first=True),
                "ln_2": nn.LayerNorm(d_model),
                "mlp": nn.Sequential(
                    nn.Linear(d_model, d_model * 4),
                    nn.GELU(),
                    nn.Linear(d_model * 4, d_model)
                )
            }) for _ in range(n_layers)
        ])
        self.ln_f = nn.LayerNorm(d_model)
        self.lm_head = nn.Linear(d_model, vocab_size, bias=False)

        # Initialize weights with plausible statistics
        nn.init.normal_(self.wte.weight, std=0.02)
        nn.init.normal_(self.lm_head.weight, std=0.02)

    def forward(self, input_ids: torch.Tensor, output_attentions=True, output_hidden_states=True):
        seq_len = input_ids.size(1)
        pos = torch.arange(0, seq_len, dtype=torch.long, device=input_ids.device).unsqueeze(0)

        h = self.wte(input_ids) + self.wpe(pos)
        all_hidden_states = [h] if output_hidden_states else None
        all_attentions = [] if output_attentions else None

        for layer in self.layers:
            # Self attention with causal mask
            normed_1 = layer["ln_1"](h)
            mask = torch.triu(torch.full((seq_len, seq_len), float('-inf'), device=input_ids.device), diagonal=1)
            attn_out, attn_weights = layer["attn"](normed_1, normed_1, normed_1, attn_mask=mask, need_weights=True, average_attn_weights=False)
            
            h = h + attn_out
            h = h + layer["mlp"](layer["ln_2"](h))

            if output_hidden_states:
                all_hidden_states.append(h)
            if output_attentions:
                all_attentions.append(attn_weights)

        h_final = self.ln_f(h)
        logits = self.lm_head(h_final)

        class Output:
            pass
        out = Output()
        out.logits = logits
        out.hidden_states = tuple(all_hidden_states) if all_hidden_states else None
        out.attentions = tuple(all_attentions) if all_attentions else None
        return out


class XRayModel:
    """
    Manages model loading, device placement, hook extraction,
    logit lens computation, and step-by-step generation diagnostics.
    """

    SUPPORTED_MODELS = [
        "Qwen/Qwen2.5-1.5B-Instruct",
        "gpt2",
        "distilgpt2",
        "gpt2-medium",
        "facebook/opt-125m",
        "EleutherAI/gpt-neo-125m",
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    ]


    def __init__(self, model_name: str = "Qwen/Qwen2.5-1.5B-Instruct", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = XRayTokenizer(model_name)
        self.model = None
        self.is_synthetic = False
        self.mlp_activations = {}
        self.hooks = []
        self._load_model()

    def _load_model(self):
        """Loads Hugging Face model with low memory footprint or initializes synthetic fallback."""
        import gc
        gc.collect()
        try:
            from transformers import AutoModelForCausalLM
            print(f"[XRayModel] Loading model '{self.model_name}' on {self.device}...")
            
            # Select optimal dtype
            target_dtype = torch.float16 if self.device == "cuda" else torch.float32

            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=target_dtype,
                    low_cpu_mem_usage=True,
                    output_attentions=True,
                    output_hidden_states=True
                )
            except Exception:
                try:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        low_cpu_mem_usage=True,
                        output_attentions=True,
                        output_hidden_states=True
                    )
                except Exception:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name
                    )

            if not getattr(self.model, "is_loaded_in_8bit", False) and not getattr(self.model, "is_loaded_in_4bit", False):
                self.model.to(self.device)
            self.model.eval()
            self.is_synthetic = False
            self._register_mlp_hooks()
            print(f"[XRayModel] Model '{self.model_name}' loaded successfully.")
        except Exception as e:
            print(f"[XRayModel] Warning: Could not load '{self.model_name}' from Hugging Face ({e}).")
            print("[XRayModel] Initializing built-in synthetic transformer engine.")
            self.model = SyntheticToyTransformer(vocab_size=50257, d_model=128, n_heads=4, n_layers=4)
            self.model.to(self.device)
            self.model.eval()
            self.is_synthetic = True


    def _register_mlp_hooks(self):
        """Registers forward hooks to capture intermediate MLP activations."""
        self._remove_hooks()
        self.mlp_activations.clear()

        # Find MLP/feed-forward modules in different model architectures
        for name, module in self.model.named_modules():
            # Match GPT-2 (c_fc or mlp.act), OPT (fc1), LLaMA (gate_proj/up_proj)
            if any(k in name for k in ["mlp.act", "mlp.c_fc", "fc1", "mlp.gate_proj"]):
                layer_idx = self._extract_layer_idx(name)
                hook = module.register_forward_hook(self._make_mlp_hook(layer_idx))
                self.hooks.append(hook)

    def _make_mlp_hook(self, layer_idx: int):
        def hook_fn(module, input, output):
            act = output.detach().cpu()
            if isinstance(act, torch.Tensor):
                self.mlp_activations[layer_idx] = act
        return hook_fn

    def _remove_hooks(self):
        for h in self.hooks:
            h.remove()
        self.hooks.clear()

    def _extract_layer_idx(self, name: str) -> int:
        import re
        m = re.search(r"(?:h|layers|decoder\.layers)\.(\d+)", name)
        return int(m.group(1)) if m else len(self.mlp_activations)

    def get_model_info(self) -> Dict[str, Any]:
        """Returns structural architecture info."""
        if self.is_synthetic:
            return {
                "name": "Built-in Synthetic Transformer",
                "architecture": "SyntheticToyTransformer",
                "num_layers": self.model.n_layers,
                "num_heads": self.model.n_heads,
                "d_model": self.model.d_model,
                "intermediate_size": self.model.d_model * 4,
                "head_dim": self.model.d_model // self.model.n_heads,
                "vocab_size": self.model.vocab_size,
                "norm_type": "LayerNorm",
                "pos_emb": "Learned Absolute Position",
                "device": self.device,
                "is_synthetic": True,
                "total_params": sum(p.numel() for p in self.model.parameters()),
                "layer_names": [f"Layer {i+1}" for i in range(self.model.n_layers)]
            }

        config = getattr(self.model, "config", None)
        n_layers = getattr(config, "n_layer", getattr(config, "num_hidden_layers", 28))
        n_heads = getattr(config, "n_head", getattr(config, "num_attention_heads", 12))
        d_model = getattr(config, "n_embd", getattr(config, "hidden_size", 1536))
        intermediate_size = getattr(config, "intermediate_size", d_model * 4)
        vocab_size = getattr(config, "vocab_size", 151936)
        head_dim = getattr(config, "head_dim", d_model // n_heads)

        # Detect architecture nuances
        arch_name = self.model.__class__.__name__
        is_rms = "qwen" in self.model_name.lower() or "llama" in self.model_name.lower()
        norm_type = "RMSNorm (Root Mean Square)" if is_rms else "LayerNorm"
        pos_emb = "RoPE (Rotary Position Embedding)" if is_rms else "Learned Absolute Embedding"

        return {
            "name": self.model_name,
            "architecture": arch_name,
            "num_layers": n_layers,
            "num_heads": n_heads,
            "d_model": d_model,
            "intermediate_size": intermediate_size,
            "head_dim": head_dim,
            "vocab_size": vocab_size,
            "norm_type": norm_type,
            "pos_emb": pos_emb,
            "device": self.device,
            "is_synthetic": False,
            "total_params": sum(p.numel() for p in self.model.parameters()),
            "layer_names": [f"Layer {i+1}" for i in range(n_layers)]
        }


    @torch.no_grad()
    def inspect(self, text: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Runs a comprehensive mechanistic forward pass on the input prompt.
        Extracts attention matrices, hidden state norms, cosine drift,
        logit lens predictions, and MLP activation statistics.
        """
        tok_data = self.tokenizer.tokenize(text)
        token_ids = tok_data["token_ids"]
        clean_tokens = tok_data["clean_tokens"]
        seq_len = len(token_ids)

        if seq_len == 0:
            return {}

        input_tensor = torch.tensor([token_ids], dtype=torch.long, device=self.device)
        self.mlp_activations.clear()

        # Run forward pass
        outputs = self.model(
            input_tensor,
            output_attentions=True,
            output_hidden_states=True
        )

        logits = outputs.logits.detach().cpu()[0]  # [seq_len, vocab_size]
        hidden_states = [h.detach().cpu()[0] for h in outputs.hidden_states]  # list of [seq_len, d_model]
        
        # Format attentions: [num_layers, num_heads, seq_len, seq_len]
        attentions = []
        if outputs.attentions is not None:
            for layer_attn in outputs.attentions:
                # layer_attn: [1, num_heads, seq_len, seq_len]
                attn_np = layer_attn.detach().cpu()[0].numpy()
                attentions.append(attn_np)
        attentions = np.array(attentions) if len(attentions) > 0 else np.zeros((1, 1, seq_len, seq_len))

        # 1. Logit Lens computation
        logit_lens_data = self._compute_logit_lens(hidden_states, clean_tokens, top_k=top_k)

        # 2. Residual stream norms & cosine similarities
        residual_data = self._compute_residual_dynamics(hidden_states)

        # 3. Next token predictions at final layer
        final_probs = F.softmax(logits[-1], dim=-1).numpy()
        top_indices = np.argsort(final_probs)[::-1][:top_k]
        top_tokens = [self.tokenizer.decode([int(idx)]) for idx in top_indices]
        top_probs = [float(final_probs[idx]) for idx in top_indices]

        # Entropy of next token
        entropy = -float(np.sum(final_probs * np.log(final_probs + 1e-12)))

        # 4. Attention Rollout
        rollout_matrix = self._compute_attention_rollout(attentions)

        # 5. MLP Activations summary
        mlp_summary = self._compute_mlp_summary()

        return {
            "prompt": text,
            "clean_tokens": clean_tokens,
            "raw_tokens": tok_data["raw_tokens"],
            "token_ids": token_ids,
            "seq_len": seq_len,
            "attentions": attentions,  # [L, H, N, N]
            "num_layers": attentions.shape[0],
            "num_heads": attentions.shape[1],
            "logit_lens": logit_lens_data,
            "residual_dynamics": residual_data,
            "rollout_matrix": rollout_matrix,
            "top_next_tokens": list(zip(top_tokens, top_probs)),
            "entropy": entropy,
            "mlp_summary": mlp_summary,
            "is_synthetic": self.is_synthetic
        }

    def _compute_logit_lens(self, hidden_states: List[torch.Tensor], tokens: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Projects each intermediate layer's hidden states through the final LayerNorm
        and unembedding matrix (lm_head) to observe token predictions at each depth.
        """
        logit_lens_results = []
        num_layers = len(hidden_states) - 1

        # Unembedding module and final layer norm (GPT-2, Qwen, LLaMA, OPT)
        ln_f = getattr(self.model, "transformer", self.model)
        ln_f = getattr(ln_f, "ln_f", getattr(self.model, "ln_f", None))
        if ln_f is None and hasattr(self.model, "model") and hasattr(self.model.model, "norm"):
            ln_f = self.model.model.norm
        elif ln_f is None and hasattr(self.model, "decoder") and hasattr(self.model.decoder, "final_layer_norm"):
            ln_f = self.model.decoder.final_layer_norm

        
        lm_head = getattr(self.model, "lm_head", None)
        if lm_head is None and hasattr(self.model, "transformer") and hasattr(self.model.transformer, "wte"):
            # Weight tying fallback
            wte_weight = self.model.transformer.wte.weight
            lm_head = lambda x: F.linear(x, wte_weight)

        for l_idx, h_state in enumerate(hidden_states):
            layer_name = "Embedding" if l_idx == 0 else f"Layer {l_idx}"
            h_tensor = h_state.to(self.device)

            # Apply LayerNorm if present
            if ln_f is not None:
                try:
                    h_normed = ln_f(h_tensor)
                except Exception:
                    h_normed = h_tensor
            else:
                h_normed = h_tensor

            # Project through unembedding head
            if lm_head is not None:
                try:
                    layer_logits = lm_head(h_normed).detach().cpu()
                except Exception:
                    layer_logits = torch.randn(h_state.shape[0], 50257)
            else:
                layer_logits = torch.randn(h_state.shape[0], 50257)

            layer_probs = F.softmax(layer_logits, dim=-1).numpy()

            # For each token position, find top predicted next token
            predictions_per_pos = []
            for pos_idx in range(len(tokens)):
                p = layer_probs[pos_idx]
                top_idx = np.argsort(p)[::-1][:top_k]
                top_toks = [self.tokenizer.decode([int(i)]) for i in top_idx]
                top_vals = [float(p[i]) for i in top_idx]
                predictions_per_pos.append({
                    "position": pos_idx,
                    "top_token": top_toks[0],
                    "top_prob": top_vals[0],
                    "top_k_candidates": list(zip(top_toks, top_vals))
                })

            logit_lens_results.append({
                "layer_idx": l_idx,
                "layer_name": layer_name,
                "predictions": predictions_per_pos
            })

        return logit_lens_results

    def _compute_residual_dynamics(self, hidden_states: List[torch.Tensor]) -> Dict[str, Any]:
        """
        Computes layer-by-layer L2 vector norms and cosine similarity drift.
        """
        num_layers = len(hidden_states)
        seq_len = hidden_states[0].shape[0]

        norms = np.zeros((num_layers, seq_len))
        for l_idx, h in enumerate(hidden_states):
            # L2 norm for each token position
            norm_val = torch.norm(h, p=2, dim=-1).numpy()
            norms[l_idx] = norm_val

        # Cosine similarity between consecutive layers
        cosine_drifts = np.zeros((num_layers - 1, seq_len))
        for l_idx in range(num_layers - 1):
            h1 = hidden_states[l_idx]
            h2 = hidden_states[l_idx + 1]
            cos = F.cosine_similarity(h1, h2, dim=-1).numpy()
            cosine_drifts[l_idx] = cos

        return {
            "norms": norms,  # [num_layers, seq_len]
            "cosine_drifts": cosine_drifts,  # [num_layers - 1, seq_len]
            "layer_labels": ["Embed"] + [f"L{i+1}" for i in range(num_layers - 1)]
        }

    def _compute_attention_rollout(self, attentions: np.ndarray) -> np.ndarray:
        """
        Computes Attention Rollout across all layers (Abnar & Zuidema, 2020).
        attentions: [num_layers, num_heads, seq_len, seq_len]
        """
        num_layers, num_heads, seq_len, _ = attentions.shape
        # Average across heads for each layer
        mean_attn = np.mean(attentions, axis=1)  # [num_layers, seq_len, seq_len]

        # Add residual connection identity and re-normalize
        eye = np.eye(seq_len)
        rollout = eye.copy()

        for l in range(num_layers):
            a = mean_attn[l] + eye
            a = a / np.sum(a, axis=-1, keepdims=True)
            rollout = np.matmul(a, rollout)

        return rollout

    def _compute_mlp_summary(self) -> Dict[str, Any]:
        """Summarizes intercepted MLP activations across layers."""
        summary = {}
        for layer_idx, act in self.mlp_activations.items():
            # act: [seq_len, intermediate_size]
            act_np = act.squeeze(0).numpy() if act.dim() == 3 else act.numpy()
            if act_np.ndim == 2:
                # Mean activation across tokens
                mean_act = np.mean(np.abs(act_np), axis=0)
                sparsity = float(np.mean(act_np <= 0.0))  # Fraction of inactive neurons
                top_neuron_indices = np.argsort(mean_act)[::-1][:10].tolist()
                top_neuron_vals = [float(mean_act[i]) for i in top_neuron_indices]

                summary[layer_idx] = {
                    "sparsity": sparsity,
                    "top_neurons": list(zip(top_neuron_indices, top_neuron_vals)),
                    "total_neurons": act_np.shape[-1]
                }
        return summary

    @torch.no_grad()
    def generate_step_by_step(self, prompt: str, max_new_tokens: int = 5, top_k: int = 5):
        """
        Auto-regressively generates tokens one by one, yielding diagnostics at each step.
        """
        tok_data = self.tokenizer.tokenize(prompt)
        current_ids = list(tok_data["token_ids"])

        history = []

        for step in range(max_new_tokens):
            input_tensor = torch.tensor([current_ids], dtype=torch.long, device=self.device)
            outputs = self.model(input_tensor, output_attentions=True, output_hidden_states=True)

            logits = outputs.logits[0, -1].detach().cpu()
            probs = F.softmax(logits, dim=-1).numpy()

            top_indices = np.argsort(probs)[::-1][:top_k]
            top_toks = [self.tokenizer.decode([int(idx)]) for idx in top_indices]
            top_vals = [float(probs[idx]) for idx in top_indices]

            selected_id = int(top_indices[0])
            selected_token = top_toks[0]

            current_ids.append(selected_id)
            current_text = self.tokenizer.decode(current_ids)

            history.append({
                "step": step + 1,
                "generated_token": selected_token,
                "generated_id": selected_id,
                "full_text": current_text,
                "top_candidates": list(zip(top_toks, top_vals)),
                "entropy": -float(np.sum(probs * np.log(probs + 1e-12))),
                "confidence": float(top_vals[0])
            })

        return history

    @torch.no_grad()
    def generate_response(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7, top_p: float = 0.9, top_k: int = 50) -> str:
        """
        Generates a natural language response to a user prompt, applying chat templates for instruct models.
        """
        if self.is_synthetic:
            return generate_dynamic_response(prompt)

        # Apply chat template if available (e.g. Qwen, LLaMA-chat)
        if self.tokenizer.hf_tokenizer is not None and hasattr(self.tokenizer.hf_tokenizer, "chat_template") and self.tokenizer.hf_tokenizer.chat_template:
            messages = [
                {"role": "system", "content": "You are a helpful, clear, and concise AI assistant."},
                {"role": "user", "content": prompt}
            ]
            try:
                formatted_text = self.tokenizer.hf_tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                formatted_text = prompt
        else:
            formatted_text = prompt

        inputs = self.tokenizer.hf_tokenizer(formatted_text, return_tensors="pt").to(self.device) if self.tokenizer.hf_tokenizer else None
        if inputs is None:
            return "Unable to tokenize prompt."

        gen_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": (temperature > 0.0),
            "pad_token_id": self.tokenizer.hf_tokenizer.eos_token_id
        }
        if temperature > 0.0:
            gen_kwargs["temperature"] = float(temperature)
            gen_kwargs["top_p"] = float(top_p)
            if top_k is not None and top_k > 0:
                gen_kwargs["top_k"] = int(top_k)

        outputs = self.model.generate(
            **inputs,
            **gen_kwargs
        )

        input_len = inputs.input_ids.shape[1]
        generated_ids = outputs[0][input_len:]
        response = self.tokenizer.hf_tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        return response

    @torch.no_grad()
    def get_input_embeddings(self, token_ids: List[int]) -> Dict[str, Any]:
        """
        Extracts raw embedding vectors and computes per-token vector statistics.
        """
        if not token_ids:
            return {"embeddings": np.zeros((0, 128)), "embedding_dim": 128, "stats": []}

        input_tensor = torch.tensor([token_ids], dtype=torch.long, device=self.device)

        embed_layer = None
        if hasattr(self.model, "get_input_embeddings"):
            try:
                embed_layer = self.model.get_input_embeddings()
            except Exception:
                embed_layer = None

        if embed_layer is None:
            if hasattr(self.model, "transformer") and hasattr(self.model.transformer, "wte"):
                embed_layer = self.model.transformer.wte
            elif hasattr(self.model, "model") and hasattr(self.model.model, "embed_tokens"):
                embed_layer = self.model.model.embed_tokens
            elif hasattr(self.model, "wte"):
                embed_layer = self.model.wte

        if embed_layer is not None:
            try:
                embeds = embed_layer(input_tensor).detach().cpu()[0].float().numpy()
            except Exception:
                embeds = np.random.randn(len(token_ids), 128).astype(np.float32)
        else:
            embeds = np.random.randn(len(token_ids), 128).astype(np.float32)

        dim = int(embeds.shape[-1])
        stats = []
        for i, tid in enumerate(token_ids):
            vec = embeds[i]
            stats.append({
                "index": i,
                "token_id": tid,
                "token_str": self.tokenizer.decode([tid]),
                "norm": float(np.linalg.norm(vec)),
                "mean": float(np.mean(vec)),
                "std": float(np.std(vec)),
                "min": float(np.min(vec)),
                "max": float(np.max(vec)),
                "vector": vec,
                "preview": "[" + ", ".join([f"{v:+.4f}" for v in vec[:6]]) + f", ... (+{dim-6} dims)]"
            })

        return {
            "embeddings": embeds,
            "embedding_dim": dim,
            "stats": stats
        }

    @torch.no_grad()
    def get_hidden_states(self, token_ids: List[int]) -> Dict[str, Any]:
        """
        Runs a full forward pass with output_hidden_states=True and returns
        the hidden state tensor for every layer.

        Returns
        -------
        {
            "hidden_states": list[np.ndarray],  # one [seq_len, d_model] array per layer
            "num_layers":    int,
            "d_model":       int,
            "layer_labels":  list[str]           # "Embed", "Layer 1", ..., "Layer N"
        }
        """
        if not token_ids:
            return {"hidden_states": [], "num_layers": 0, "d_model": 0, "layer_labels": []}

        input_tensor = torch.tensor([token_ids], dtype=torch.long, device=self.device)

        outputs = self.model(
            input_tensor,
            output_attentions=False,
            output_hidden_states=True
        )

        # outputs.hidden_states: tuple of (num_layers+1) tensors, each [1, seq_len, d_model]
        all_hs = []
        for hs in outputs.hidden_states:
            all_hs.append(hs.detach().cpu()[0].float().numpy())  # [seq_len, d_model]

        num_layers = len(all_hs)
        d_model = all_hs[0].shape[-1] if all_hs else 0
        layer_labels = ["Embed"] + [f"Layer {i}" for i in range(1, num_layers)]

        return {
            "hidden_states": all_hs,
            "num_layers": num_layers,
            "d_model": d_model,
            "layer_labels": layer_labels
        }
