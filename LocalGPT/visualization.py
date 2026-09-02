"""
LocalGPT: Visualization Engine
Provides interactive Plotly figures and custom UI visualizers for
Attention Maps, Logit Lens, Residual Stream, and Neuron Activations.
"""

from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


# Consistent dark theme styling tokens
DARK_LAYOUT = dict(
    paper_bgcolor="rgba(15, 20, 32, 0.85)",
    plot_bgcolor="rgba(18, 24, 38, 0.95)",
    font=dict(color="#E2E8F0", family="Inter, system-ui, sans-serif"),
)


def format_token_labels(tokens: List[str]) -> List[str]:
    """Formats token strings with indices and visible whitespace symbols for axis labels."""
    formatted = []
    for i, t in enumerate(tokens):
        # Clean visible representation
        disp = t.replace(" ", "·").replace("\n", "↵")
        if len(disp) > 12:
            disp = disp[:10] + ".."
        formatted.append(f"[{i}] {disp}")
    return formatted


def plot_attention_heatmap(
    tokens: List[str],
    attention_matrix: np.ndarray,
    layer_idx: int,
    head_idx: int,
    colorscale: str = "Viridis"
) -> go.Figure:
    """
    Renders an interactive heatmap for a single attention head at Layer L, Head H.
    attention_matrix shape: [seq_len, seq_len] (queries x keys)
    """
    labels = format_token_labels(tokens)
    seq_len = len(tokens)

    # Hover text matrix
    hover_text = []
    for i in range(seq_len):
        row_text = []
        for j in range(seq_len):
            val = attention_matrix[i, j]
            row_text.append(
                f"<b>Layer {layer_idx} | Head {head_idx}</b><br>"
                f"Query (Looking from): <b>{labels[i]}</b><br>"
                f"Key (Attending to): <b>{labels[j]}</b><br>"
                f"Attention Weight: <b>{val * 100:.2f}%</b> ({val:.4f})"
            )
        hover_text.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=attention_matrix,
        x=labels,
        y=labels,
        colorscale=colorscale,
        colorbar=dict(
            title=dict(text="Weight", font=dict(color="#E2E8F0")),
            tickfont=dict(color="#CBD5E1"),
            thickness=15
        ),
        hovertemplate="%{text}<extra></extra>",
        text=hover_text,
        zmin=0.0,
        zmax=max(1.0, float(np.max(attention_matrix)))
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text=f"🔍 <b>Self-Attention Map — Layer {layer_idx}, Head {head_idx}</b>",
            font=dict(size=18, color="#38BDF8")
        ),
        xaxis=dict(
            title="<b>Key Tokens (Attended To)</b>",
            tickangle=-45,
            gridcolor="rgba(255,255,255,0.05)",
            color="#94A3B8"
        ),
        yaxis=dict(
            title="<b>Query Tokens (Source)</b>",
            autorange="reversed",
            gridcolor="rgba(255,255,255,0.05)",
            color="#94A3B8"
        ),
        height=max(450, 40 * seq_len + 150),
    )
    return fig


def plot_multi_head_grid(
    tokens: List[str],
    attention_matrices: np.ndarray,
    layer_idx: int,
    cols: int = 4
) -> go.Figure:
    """
    Renders a multi-panel subplot grid displaying all attention heads in a single layer.
    attention_matrices shape: [num_heads, seq_len, seq_len]
    """
    num_heads = attention_matrices.shape[0]
    rows = int(np.ceil(num_heads / cols))
    labels = [f"{i}:{t[:4]}" for i, t in enumerate(tokens)]

    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=[f"Head {h}" for h in range(num_heads)],
        horizontal_spacing=0.04,
        vertical_spacing=0.08
    )

    for h in range(num_heads):
        r = (h // cols) + 1
        c = (h % cols) + 1
        mat = attention_matrices[h]

        fig.add_trace(
            go.Heatmap(
                z=mat,
                x=labels,
                y=labels,
                colorscale="Plasma",
                showscale=False,
                hoverinfo="z"
            ),
            row=r,
            col=c
        )
        fig.update_yaxes(autorange="reversed", row=r, col=c, showticklabels=False)
        fig.update_xaxes(showticklabels=False, row=r, col=c)

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text=f"🧩 <b>Multi-Head Attention Overview — Layer {layer_idx} ({num_heads} Heads)</b>",
            font=dict(size=18, color="#F472B6")
        ),
        height=max(500, rows * 180),
    )
    return fig


def plot_attention_rollout(
    tokens: List[str],
    rollout_matrix: np.ndarray
) -> go.Figure:
    """
    Renders the Attention Rollout matrix (global information flow across all layers).
    """
    labels = format_token_labels(tokens)
    seq_len = len(tokens)

    fig = go.Figure(data=go.Heatmap(
        z=rollout_matrix,
        x=labels,
        y=labels,
        colorscale="Turbo",
        colorbar=dict(
            title="Flow %",
            tickfont=dict(color="#CBD5E1"),
            thickness=15
        ),
        hovertemplate="Source: %{y}<br>Target: %{x}<br>Rollout Flow: %{z:.4f}<extra></extra>"
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="🌊 <b>Attention Rollout (End-to-End Information Flow)</b>",
            font=dict(size=18, color="#A78BFA")
        ),
        xaxis=dict(title="Input Token", tickangle=-45, gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="Output Token Position", autorange="reversed", gridcolor="rgba(255,255,255,0.05)"),
        height=max(450, 40 * seq_len + 150)
    )
    return fig


def plot_logit_lens_matrix(
    tokens: List[str],
    logit_lens_data: List[Dict[str, Any]]
) -> go.Figure:
    """
    Creates the iconic Logit Lens progression heatmap.
    Shows the top predicted token and confidence at each layer for each position.
    """
    num_layers = len(logit_lens_data)
    seq_len = len(tokens)
    token_labels = format_token_labels(tokens)
    layer_labels = [d["layer_name"] for d in logit_lens_data]

    conf_matrix = np.zeros((num_layers, seq_len))
    text_matrix = []
    hover_text = []

    for l_idx, l_data in enumerate(logit_lens_data):
        row_text = []
        row_hover = []
        for pos_idx, pred in enumerate(l_data["predictions"]):
            top_tok = pred["top_token"].replace(" ", "·").replace("\n", "↵")
            prob = pred["top_prob"]
            conf_matrix[l_idx, pos_idx] = prob
            
            # Text inside cell
            row_text.append(f"{top_tok}<br><b>{prob*100:.0f}%</b>")
            
            # Tooltip
            cands_str = "<br>".join([f"&nbsp;&nbsp;• <b>{c[0]}</b>: {c[1]*100:.1f}%" for c in pred["top_k_candidates"][:3]])
            row_hover.append(
                f"<b>{layer_labels[l_idx]}</b> | Position: <b>{token_labels[pos_idx]}</b><br>"
                f"Top Prediction: <b>'{pred['top_token']}'</b> ({prob*100:.2f}%)<br>"
                f"Candidates:<br>{cands_str}"
            )
        text_matrix.append(row_text)
        hover_text.append(row_hover)

    fig = go.Figure(data=go.Heatmap(
        z=conf_matrix,
        x=token_labels,
        y=layer_labels,
        text=text_matrix,
        texttemplate="%{text}",
        textfont=dict(size=11, color="#FFFFFF"),
        colorscale="Inferno",
        colorbar=dict(
            title="Confidence",
            tickfont=dict(color="#CBD5E1"),
            thickness=15
        ),
        hovertemplate="%{hovertext}<extra></extra>",
        hovertext=hover_text,
        zmin=0.0,
        zmax=1.0
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="🔭 <b>Logit Lens — Intermediate Layer Predictions</b>",
            font=dict(size=18, color="#FBBF24")
        ),
        xaxis=dict(
            title="<b>Token Position</b>",
            tickangle=-45,
            gridcolor="rgba(255,255,255,0.05)"
        ),
        yaxis=dict(
            title="<b>Transformer Layer Depth</b>",
            autorange="reversed",
            gridcolor="rgba(255,255,255,0.05)"
        ),
        height=max(480, 45 * num_layers + 160)
    )
    return fig


def plot_residual_stream_dynamics(
    residual_data: Union[Dict[str, Any], List[str]],
    tokens: Optional[Union[List[str], Dict[str, Any]]] = None
) -> Tuple[go.Figure, go.Figure]:
    """
    Plots:
    1. Layer-wise L2 Norm growth of hidden state representations.
    2. Cosine Similarity between layer l and layer l+1 (representation drift).
    """
    # Handle argument order flexibility: (tokens, residual_data) vs (residual_data, tokens)
    if isinstance(residual_data, (list, tuple)) and isinstance(tokens, dict):
        residual_data, tokens = tokens, list(residual_data)
    elif tokens is None and isinstance(residual_data, dict):
        tokens = [f"Tok_{i}" for i in range(residual_data.get("norms", np.zeros((1, 1))).shape[1])]

    norms = residual_data["norms"]  # [num_layers, seq_len]
    cosine_drifts = residual_data["cosine_drifts"]  # [num_layers - 1, seq_len]
    layer_labels = residual_data["layer_labels"]
    drift_labels = [f"{layer_labels[i]} ➔ {layer_labels[i+1]}" for i in range(len(layer_labels)-1)]

    # 1. Norm Plot
    fig_norm = go.Figure()
    for pos_idx, tok in enumerate(tokens):
        fig_norm.add_trace(go.Scatter(
            x=layer_labels,
            y=norms[:, pos_idx],
            mode="lines+markers",
            name=f"[{pos_idx}] {tok[:8]}",
            line=dict(width=2),
            marker=dict(size=6)
        ))

    fig_norm.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="📈 <b>Residual Stream L2 Norm Progression</b>",
            font=dict(size=16, color="#34D399")
        ),
        xaxis=dict(title="Layer Depth", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="Hidden State L2 Norm", gridcolor="rgba(255,255,255,0.05)"),
        height=380
    )

    # 2. Cosine Drift Plot
    fig_drift = go.Figure()
    for pos_idx, tok in enumerate(tokens):
        fig_drift.add_trace(go.Scatter(
            x=drift_labels,
            y=cosine_drifts[:, pos_idx],
            mode="lines+markers",
            name=f"[{pos_idx}] {tok[:8]}",
            line=dict(width=2),
            marker=dict(size=6)
        ))

    fig_drift.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="🔄 <b>Layer-to-Layer Cosine Similarity (Directional Stability)</b>",
            font=dict(size=16, color="#60A5FA")
        ),
        xaxis=dict(title="Layer Transition", tickangle=-30, gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="Cosine Similarity", range=[-0.1, 1.05], gridcolor="rgba(255,255,255,0.05)"),
        height=380
    )

    return fig_norm, fig_drift


def plot_top_logits_bar(top_candidates: List[Tuple[str, float]]) -> go.Figure:
    """
    Renders a bar chart showing top next-token candidates and their probabilities.
    """
    toks = [f"<b>'{c[0]}'</b>" for c in top_candidates][::-1]
    probs = [c[1] * 100 for c in top_candidates][::-1]

    fig = go.Figure(go.Bar(
        x=probs,
        y=toks,
        orientation="h",
        marker=dict(
            color=probs,
            colorscale="Viridis",
            line=dict(color="#38BDF8", width=1.5)
        ),
        text=[f"{p:.2f}%" for p in probs],
        textposition="outside",
        hovertemplate="Candidate: %{y}<br>Probability: <b>%{x:.2f}%</b><extra></extra>"
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="🎯 <b>Next-Token Probabilities</b>",
            font=dict(size=16, color="#38BDF8")
        ),
        xaxis=dict(title="Probability (%)", range=[0, max(probs) * 1.25 + 5], gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="", color="#E2E8F0"),
        height=320,
    )
    return fig


def plot_generation_timeline(generation_history: List[Dict[str, Any]]) -> go.Figure:
    """
    Renders generation progression showing step confidence and entropy dynamics.
    """
    steps = [h["step"] for h in generation_history]
    confidences = [h["confidence"] * 100 for h in generation_history]
    entropies = [h["entropy"] for h in generation_history]
    tokens = [f"'{h['generated_token']}'" for h in generation_history]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=steps,
            y=confidences,
            name="Confidence (%)",
            mode="lines+markers+text",
            text=tokens,
            textposition="top center",
            line=dict(color="#34D399", width=3),
            marker=dict(size=10, symbol="circle")
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=steps,
            y=entropies,
            name="Entropy (nats)",
            mode="lines+markers",
            line=dict(color="#F43F5E", width=2, dash="dot"),
            marker=dict(size=8, symbol="diamond")
        ),
        secondary_y=True
    )

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="📊 <b>Autoregressive Generation Dynamics (Confidence vs. Uncertainty)</b>",
            font=dict(size=16, color="#A78BFA")
        ),
        xaxis=dict(title="Generation Step", gridcolor="rgba(255,255,255,0.05)"),
        height=360
    )
    fig.update_yaxes(title_text="Confidence (%)", secondary_y=False, range=[0, 110])
    fig.update_yaxes(title_text="Entropy (Uncertainty)", secondary_y=True)

    return fig


def plot_neuron_sparsity(mlp_summary: Dict[Any, Any]) -> Optional[go.Figure]:
    """
    Plots activation sparsity and top firing neuron magnitude across layers.
    """
    if not mlp_summary:
        return None

    layers = list(mlp_summary.keys())
    sparsities = [mlp_summary[l]["sparsity"] * 100 for l in layers]
    layer_names = [f"L{l}" for l in layers]

    fig = go.Figure(go.Bar(
        x=layer_names,
        y=sparsities,
        marker=dict(
            color=sparsities,
            colorscale="Plasma",
            line=dict(color="#EC4899", width=1.5)
        ),
        text=[f"{s:.1f}%" for s in sparsities],
        textposition="outside"
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="⚡ <b>MLP Activation Sparsity per Layer (% Inactive Neurons)</b>",
            font=dict(size=16, color="#F472B6")
        ),
        xaxis=dict(title="Layer", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="Sparsity (%)", range=[0, 105], gridcolor="rgba(255,255,255,0.05)"),
        height=320
    )
    return fig


def plot_embedding_pca_2d(
    tokens: List[str],
    token_ids: List[int],
    embeddings: np.ndarray
) -> go.Figure:
    """
    Projects high-dimensional token embeddings onto 2D space using PCA
    and renders an interactive trajectory scatter plot.
    """
    from sklearn.decomposition import PCA

    seq_len, dim = embeddings.shape

    if seq_len >= 2:
        n_comp = min(2, seq_len, dim)
        pca = PCA(n_components=n_comp)
        coords = pca.fit_transform(embeddings)
        if n_comp == 1:
            coords = np.column_stack([coords, np.zeros(seq_len)])
            var_explained = [float(pca.explained_variance_ratio_[0]) * 100, 0.0]
        else:
            var_explained = [float(v) * 100 for v in pca.explained_variance_ratio_[:2]]
    else:
        coords = np.array([[0.0, 0.0]])
        var_explained = [100.0, 0.0]

    labels = format_token_labels(tokens)
    
    # Calculate stats per token
    norms = np.linalg.norm(embeddings, axis=-1)
    means = np.mean(embeddings, axis=-1)
    stds = np.std(embeddings, axis=-1)

    hover_texts = []
    for i in range(seq_len):
        tid = token_ids[i] if i < len(token_ids) else 0
        hover_texts.append(
            f"<b>Token #{i}: '{tokens[i]}'</b><br>"
            f"Token ID: <b>{tid}</b><br>"
            f"PC1: <b>{coords[i, 0]:.4f}</b> | PC2: <b>{coords[i, 1]:.4f}</b><br>"
            f"L2 Norm (||v||): <b>{norms[i]:.4f}</b><br>"
            f"Mean: <b>{means[i]:.4f}</b> | Std: <b>{stds[i]:.4f}</b>"
        )

    fig = go.Figure()

    # Trajectory line connecting tokens in prompt order
    if seq_len > 1:
        fig.add_trace(go.Scatter(
            x=coords[:, 0],
            y=coords[:, 1],
            mode="lines",
            line=dict(color="rgba(56, 189, 248, 0.4)", width=2, dash="dash"),
            showlegend=False,
            hoverinfo="skip"
        ))

    # Token Scatter Points
    fig.add_trace(go.Scatter(
        x=coords[:, 0],
        y=coords[:, 1],
        mode="markers+text",
        marker=dict(
            size=14,
            color=np.arange(seq_len),
            colorscale="Viridis",
            showscale=False,
            line=dict(color="#38BDF8", width=2)
        ),
        text=labels,
        textposition="top center",
        textfont=dict(size=12, color="#F8FAFC"),
        hovertemplate="%{text}<extra></extra>",
        texttemplate="%{text}",
        hovertext=hover_texts,
        name="Tokens"
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text="🧭 <b>2D Token Embedding Space (PCA Projection)</b>",
            font=dict(size=16, color="#38BDF8")
        ),
        xaxis=dict(
            title=f"<b>Principal Component 1 ({var_explained[0]:.1f}% var)</b>",
            gridcolor="rgba(255,255,255,0.08)",
            zerolinecolor="rgba(255,255,255,0.2)"
        ),
        yaxis=dict(
            title=f"<b>Principal Component 2 ({var_explained[1]:.1f}% var)</b>",
            gridcolor="rgba(255,255,255,0.08)",
            zerolinecolor="rgba(255,255,255,0.2)"
        ),
        height=450
    )
    return fig


def generate_ascii_attention_matrix(tokens: List[str], attn_matrix: np.ndarray) -> str:
    """
    Renders an ASCII / block character representation of the attention matrix.
    """
    clean_toks = [t.strip().replace("\n", "↵") if t.strip() else "·" for t in tokens]
    col_width = max(max(len(t) for t in clean_toks) + 2, 6)

    # Header row
    header = f"{'':<{col_width}} " + "".join(f"{t:^{col_width}}" for t in clean_toks)
    lines = [header]

    for i, t in enumerate(clean_toks):
        row = f"{t:<{col_width}} "
        for j in range(len(clean_toks)):
            val = float(attn_matrix[i, j])
            if val >= 0.4:
                sym = "█"
            elif val >= 0.2:
                sym = "▓"
            elif val >= 0.08:
                sym = "▒"
            else:
                sym = "░"
            row += f"{sym:^{col_width}}"
        lines.append(row)

    return "\n".join(lines)


def plot_hidden_state_pca(
    tokens: List[str],
    hidden_state: np.ndarray,
    layer_label: str,
    color_seed: int = 0
) -> go.Figure:
    """
    Projects the hidden-state matrix of ONE layer onto 2D via PCA and returns
    an interactive scatter plot, with a trajectory line connecting tokens in order.
    """
    from sklearn.decomposition import PCA

    seq_len, d_model = hidden_state.shape

    if seq_len >= 2:
        n_comp = min(2, seq_len, d_model)
        pca = PCA(n_components=n_comp, random_state=42)
        coords = pca.fit_transform(hidden_state)
        if n_comp == 1:
            coords = np.column_stack([coords, np.zeros(seq_len)])
            var_exp = [float(pca.explained_variance_ratio_[0]) * 100, 0.0]
        else:
            var_exp = [float(v) * 100 for v in pca.explained_variance_ratio_[:2]]
    else:
        coords = np.zeros((seq_len, 2))
        var_exp = [100.0, 0.0]

    # Per-token stats for hover
    norms  = np.linalg.norm(hidden_state, axis=-1)
    means  = np.mean(hidden_state, axis=-1)
    stds   = np.std(hidden_state, axis=-1)

    hover_texts = []
    for i in range(seq_len):
        hover_texts.append(
            f"<b>Token #{i}: '{tokens[i]}'</b><br>"
            f"PC1: <b>{coords[i, 0]:.4f}</b>  PC2: <b>{coords[i, 1]:.4f}</b><br>"
            f"L2 Norm: <b>{norms[i]:.4f}</b><br>"
            f"Mean: <b>{means[i]:.4f}</b>  Std: <b>{stds[i]:.4f}</b>"
        )

    labels = [f"[{i}] {t}" for i, t in enumerate(tokens)]
    colors = np.arange(seq_len) + color_seed

    fig = go.Figure()

    # Dashed trajectory line
    if seq_len > 1:
        fig.add_trace(go.Scatter(
            x=coords[:, 0], y=coords[:, 1],
            mode="lines",
            line=dict(color="rgba(167, 139, 250, 0.35)", width=2, dash="dash"),
            showlegend=False, hoverinfo="skip"
        ))

    # Token scatter
    fig.add_trace(go.Scatter(
        x=coords[:, 0], y=coords[:, 1],
        mode="markers+text",
        marker=dict(
            size=15, color=colors, colorscale="Plasma",
            showscale=True,
            colorbar=dict(
                title=dict(text="Token #", font=dict(color="#CBD5E1")),
                tickfont=dict(color="#CBD5E1"), thickness=12
            ),
            line=dict(color="#A78BFA", width=1.5)
        ),
        text=labels,
        textposition="top center",
        textfont=dict(size=11, color="#F8FAFC"),
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
        name="Tokens"
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text=f"🧬 <b>Hidden State Space — {layer_label} (2D PCA)</b>",
            font=dict(size=16, color="#A78BFA")
        ),
        xaxis=dict(
            title=f"<b>PC 1 ({var_exp[0]:.1f}% var)</b>",
            gridcolor="rgba(255,255,255,0.07)",
            zerolinecolor="rgba(255,255,255,0.18)"
        ),
        yaxis=dict(
            title=f"<b>PC 2 ({var_exp[1]:.1f}% var)</b>",
            gridcolor="rgba(255,255,255,0.07)",
            zerolinecolor="rgba(255,255,255,0.18)"
        ),
        height=420
    )
    return fig


def plot_top_logits_probabilities(
    top_tokens: list,
    top_probs: list,
    top_k: int = 10
) -> go.Figure:
    """
    Renders a horizontal bar chart showing the top-K next-token predictions
    with their softmax probabilities (as percentages).
    """
    tokens  = top_tokens[:top_k]
    probs   = top_probs[:top_k]
    pct     = [p * 100 for p in probs]

    # Colour gradient: bright violet → soft purple
    n = len(tokens)
    colours = [
        f"rgba({int(139 + 80 * (1 - i / max(n - 1, 1)))}, "
        f"{int(92  + 60 * (1 - i / max(n - 1, 1)))}, "
        f"246, {0.95 - 0.35 * (i / max(n - 1, 1)):.2f})"
        for i in range(n)
    ]

    hover = [
        f"<b>Token: '{t}'</b><br>Probability: <b>{p:.2f}%</b><br>Raw value: {r:.4f}"
        for t, p, r in zip(tokens, pct, probs)
    ]

    fig = go.Figure(go.Bar(
        x=pct,
        y=[f"'{t}'" for t in tokens],
        orientation="h",
        marker=dict(color=colours, line=dict(color="rgba(255,255,255,0.05)", width=0.5)),
        text=[f"{p:.1f}%" for p in pct],
        textposition="outside",
        textfont=dict(color="#F8FAFC", size=12),
        hovertext=hover,
        hovertemplate="%{hovertext}<extra></extra>",
        name="Probability"
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text=(
                "🎯 <b>Top Next-Token Predictions</b><br>"
                "<sup>Hidden State → LM Head → Logits → Softmax → Probabilities</sup>"
            ),
            font=dict(size=15, color="#A78BFA"),
            x=0.01
        ),
        xaxis=dict(
            title="<b>Probability (%)</b>",
            range=[0, max(pct) * 1.25 if pct else 100],
            gridcolor="rgba(255,255,255,0.07)",
            ticksuffix="%"
        ),
        yaxis=dict(
            title="<b>Token</b>",
            autorange="reversed",
            tickfont=dict(size=13, color="#E2E8F0"),
            gridcolor="rgba(255,255,255,0.04)"
        ),
        height=max(320, 42 * n + 100),
        margin=dict(l=80, r=80, t=90, b=50),
        bargap=0.28
    )
    return fig


def generate_token_probability_bars(
    top_tokens: List[str],
    top_probs: List[float],
    max_bar_len: int = 24
) -> str:
    """
    Renders clean text/ASCII probability bars matching:
    Next Token Prediction
    "is"   █████████████ 32%
    "was"  ███████ 18%
    "can"  █████ 12%
    "will" ███ 8%
    """
    if not top_tokens or not top_probs:
        return "No prediction data available."

    lines = ["Next Token Prediction:"]
    # Find max token string length for neat alignment
    max_tok_len = max(len(f'"{t.strip()}"') for t in top_tokens[:8])
    max_tok_len = max(max_tok_len, 6)

    max_prob = max(top_probs) if top_probs else 1.0

    for tok, prob in zip(top_tokens[:8], top_probs[:8]):
        tok_clean = tok.replace("\n", "↵").strip()
        tok_str = f'"{tok_clean}"' if tok_clean else '"<space>"'
        pct = prob * 100

        # Bar block computation
        num_blocks = int(round((prob / max(max_prob, 1e-6)) * max_bar_len))
        num_blocks = max(1 if pct >= 1 else 0, num_blocks)
        bar = "█" * num_blocks

        lines.append(f"{tok_str:<{max_tok_len}} {bar} {pct:.0f}% ({prob:.3f})")

    return "\n".join(lines)


def render_token_probability_html(
    top_tokens: List[str],
    top_probs: List[float],
    top_k: int = 6
) -> str:
    """
    Renders an HTML widget for Next Token Probability View with smooth gradients.
    """
    if not top_tokens or not top_probs:
        return ""

    items_html = []
    max_p = max(top_probs[:top_k]) if top_probs else 1.0

    for i, (t, p) in enumerate(zip(top_tokens[:top_k], top_probs[:top_k])):
        t_disp = t.replace(" ", "·").replace("\n", "↵")
        if not t_disp:
            t_disp = "·"
        pct = p * 100
        rel_width = min(100, max(4, int((p / max(max_p, 1e-6)) * 100)))

        # Gradient from glowing purple to cyan
        items_html.append(f"""
<div style="display:flex;align-items:center;margin:6px 0;font-family:'JetBrains Mono',monospace;font-size:0.84rem;">
  <div style="width:110px;color:#e6edf3;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
    "{t_disp}"
  </div>
  <div style="flex:1;background:rgba(255,255,255,0.06);border-radius:6px;height:20px;overflow:hidden;margin:0 12px;position:relative;">
    <div style="width:{rel_width}%;background:linear-gradient(90deg, #8b5cf6, #38bdf8);height:100%;border-radius:6px;transition:width 0.3s ease;"></div>
  </div>
  <div style="width:55px;text-align:right;color:#38bdf8;font-weight:700;">
    {pct:.1f}%
  </div>
</div>
""")

    return f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;margin:10px 0;">
  <div style="font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#a78bfa;margin-bottom:10px;">
    🎯 Next Token Prediction (Probability Distribution)
  </div>
  {''.join(items_html)}
</div>
"""

