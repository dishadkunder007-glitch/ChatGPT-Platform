import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import streamlit as st
import numpy as np
import pandas as pd
import torch

from tokenizer import XRayTokenizer
from model import XRayModel
from visualization import (
    plot_attention_heatmap,
    plot_multi_head_grid,
    plot_attention_rollout,
    plot_logit_lens_matrix,
    plot_residual_stream_dynamics,
    plot_top_logits_bar,
    plot_neuron_sparsity,
    plot_embedding_pca_2d,
    plot_hidden_state_pca,
    plot_top_logits_probabilities
)

try:
    from visualization import generate_ascii_attention_matrix
except (ImportError, AttributeError):
    def generate_ascii_attention_matrix(tokens, attn_matrix):
        clean_toks = [t.strip().replace("\n", "↵") if t.strip() else "·" for t in tokens]
        col_width = max(max(len(t) for t in clean_toks) + 2, 6) if clean_toks else 6
        header = f"{'':<{col_width}} " + "".join(f"{t:^{col_width}}" for t in clean_toks)
        lines = [header]
        for i, t in enumerate(clean_toks):
            row = f"{t:<{col_width}} "
            for j in range(len(clean_toks)):
                val = float(attn_matrix[i, j])
                if val >= 0.4:    sym = "█"
                elif val >= 0.2:  sym = "▓"
                elif val >= 0.08: sym = "▒"
                else:             sym = "░"
                row += f"{sym:^{col_width}}"
            lines.append(row)
        return "\n".join(lines)


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LLM X-RAY",
    page_icon="🔬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-color: #0B1120;
    --card-bg: #1E293B;
    --border-color: #334155;
    --accent-cyan: #38BDF8;
    --accent-violet: #A78BFA;
    --text-main: #F8FAFC;
    --text-sub: #94A3B8;
}

html, body, .stApp {
    background-color: var(--bg-color);
    color: var(--text-main);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

#MainMenu, footer, header {
    visibility: hidden;
}

/* Main Container Frame */
.xray-frame {
    border: 2px solid var(--border-color);
    border-radius: 16px;
    background: var(--card-bg);
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
    margin: 4px auto 18px auto;
    overflow: hidden;
}

/* Header Title Box */
.xray-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.14), rgba(167, 139, 250, 0.14));
    border-bottom: 2px solid var(--border-color);
    padding: 16px 24px;
}

.xray-title {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: 2.5px;
    color: #FFFFFF;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}

.xray-model-badge {
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: var(--accent-cyan);
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-radius: 20px;
    padding: 4px 14px;
    letter-spacing: 0.5px;
}

/* Prompt Card Box */
.xray-prompt-label {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-main);
    margin-bottom: 8px;
    font-family: 'Inter', sans-serif;
}

/* Response Box Frame */
.xray-response-box {
    border: 1.5px solid #475569;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.9);
    padding: 18px 22px;
    margin-top: 18px;
    margin-bottom: 10px;
}

.xray-response-label {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--accent-cyan);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.xray-response-text {
    font-size: 1.02rem;
    line-height: 1.7;
    color: #F1F5F9;
    white-space: pre-wrap;
}

/* Chips */
.tok-chip {
    display: inline-block;
    background: rgba(56, 189, 248, 0.14);
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 6px;
    padding: 3px 9px;
    margin: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #E0F2FE;
}

.tok-id-chip {
    display: inline-block;
    background: rgba(167, 139, 250, 0.14);
    border: 1px solid rgba(167, 139, 250, 0.4);
    border-radius: 6px;
    padding: 3px 9px;
    margin: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #DDD6FE;
}

/* Pipeline Box */
.pipeline-flow {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 8px;
    padding: 10px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #38BDF8;
    margin-bottom: 14px;
    text-align: center;
}

/* Tab Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 5px;
    margin-bottom: 12px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    padding: 6px 14px;
    color: var(--text-sub);
    font-weight: 600;
    font-size: 0.85rem;
    background: transparent;
    border: none;
    transition: all 0.15s ease-in-out;
}

.stTabs [aria-selected="true"] {
    color: #FFFFFF !important;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.28), rgba(167, 139, 250, 0.28)) !important;
    border: 1px solid rgba(56, 189, 248, 0.4) !important;
}

/* ── Modern Vibrant Blue Buttons ── */
button[data-testid="stBaseButton-primary"],
div.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 50%, #3b82f6 100%) !important;
    color: #ffffff !important;
    border: 1px solid #60a5fa !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4) !important;
    transition: all 0.2s ease-in-out !important;
}
button[data-testid="stBaseButton-primary"]:hover,
div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb 0%, #3b82f6 50%, #60a5fa 100%) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6) !important;
    transform: translateY(-1px);
}

button[data-testid="stBaseButton-secondary"],
div.stButton > button {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
    color: #93c5fd !important;
    border: 1px solid rgba(59, 130, 246, 0.4) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease-in-out !important;
}
button[data-testid="stBaseButton-secondary"]:hover,
div.stButton > button:hover {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border-color: #60a5fa !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)


# ── Model Configuration & Loading ─────────────────────────────────────────────
DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

with st.sidebar:
    st.markdown("### ⚙️ **Model & System**")
    model_choice = st.selectbox(
        "Model Architecture",
        [DEFAULT_MODEL, "gpt2", "distilgpt2", "gpt2-medium", "facebook/opt-125m", "Custom Model..."],
        index=0
    )
    if model_choice == "Custom Model...":
        selected_model_name = st.text_input("Enter HuggingFace Model ID", value=DEFAULT_MODEL)
    else:
        selected_model_name = model_choice

    device_str = "cuda" if torch.cuda.is_available() else "cpu"
    st.caption(f"Hardware Accelerator: **{device_str.upper()}**")

@st.cache_resource(show_spinner="Loading model weights…")
def get_model(name: str):
    return XRayModel(model_name=name)

xray = get_model(selected_model_name)
model_info = xray.get_model_info()

num_layers = model_info.get("num_layers", 28)
num_heads  = model_info.get("num_heads",  12)
d_model    = model_info.get("d_model",    1536)
head_dim   = model_info.get("head_dim",   d_model // num_heads if num_heads else 128)
d_ff       = model_info.get("intermediate_size", d_model * 4)
norm_type  = model_info.get("norm_type",  "RMSNorm")


# ── Cached Computations for Fast Tab Switching ────────────────────────────────
@st.cache_data(show_spinner=False)
def cached_inspect(prompt: str, top_k: int):
    return xray.inspect(prompt, top_k=top_k)

@st.cache_data(show_spinner=False)
def cached_embeddings(token_ids_tuple: tuple):
    return xray.get_input_embeddings(list(token_ids_tuple))

@st.cache_data(show_spinner=False)
def cached_hidden_states(token_ids_tuple: tuple):
    return xray.get_hidden_states(list(token_ids_tuple))


# ── Session State Initialization ──────────────────────────────────────────────
if "prompt_input" not in st.session_state:
    st.session_state["prompt_input"] = "Explain Machine Learning"

if "response_text" not in st.session_state:
    st.session_state["response_text"] = (
        "Machine learning is a branch of artificial intelligence (AI) and computer science "
        "that focuses on using data and algorithms to enable machines to imitate the way that "
        "humans learn, gradually improving their accuracy over time."
    )


# ── 5. Final Interface: Header ─────────────────────────────────────────────────
display_model_badge = "Qwen2.5-1.5B-Instruct" if "qwen" in selected_model_name.lower() else selected_model_name.split("/")[-1]

st.markdown(f"""
<div class="xray-frame">
  <div class="xray-header">
    <span class="xray-title">LLM X-RAY</span>
    <span class="xray-model-badge">{display_model_badge}</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Prompt Input Section ──────────────────────────────────────────────────────
st.markdown('<div class="xray-prompt-label">Enter your prompt</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([4.2, 1.2])
with col_input:
    prompt_text = st.text_area(
        "Prompt Input",
        value=st.session_state["prompt_input"],
        height=82,
        key="main_prompt_text",
        label_visibility="collapsed",
        placeholder="Enter your prompt here..."
    )

with col_btn:
    st.write("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    generate_btn = st.button("⚡ Generate", type="primary", use_container_width=True, key="main_gen_btn")


# ── 6. Optional Controls Section ──────────────────────────────────────────────
with st.expander("⚙️ **Optional Controls**", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        opt_temp = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.05, key="opt_temp_ctrl")
        opt_max_tokens = st.slider("Maximum new tokens", min_value=16, max_value=512, value=128, step=16, key="opt_max_tokens_ctrl")
    with c2:
        opt_top_k = st.slider("Top-K", min_value=1, max_value=50, value=10, step=1, key="opt_top_k_ctrl")
        opt_top_p = st.slider("Top-P", min_value=0.05, max_value=1.0, value=0.9, step=0.05, key="opt_top_p_ctrl")
    with c3:
        opt_layer = st.number_input("Transformer layer", min_value=1, max_value=num_layers, value=min(12, num_layers), key="opt_layer_ctrl")
        opt_head = st.number_input("Attention head", min_value=1, max_value=num_heads, value=min(4, num_heads), key="opt_head_ctrl")


# ── Execute Generation ────────────────────────────────────────────────────────
if generate_btn:
    if not prompt_text.strip():
        st.warning("Please enter a prompt before generating.")
    else:
        st.session_state["prompt_input"] = prompt_text.strip()
        with st.spinner("Generating response with LLM X-Ray..."):
            gen_resp = xray.generate_response(
                prompt_text.strip(),
                max_new_tokens=int(opt_max_tokens),
                temperature=float(opt_temp),
                top_p=float(opt_top_p),
                top_k=int(opt_top_k)
            )
            st.session_state["response_text"] = gen_resp


# ── Tokenize Current Prompt ───────────────────────────────────────────────────
clean_toks, token_ids = [], []
if prompt_text.strip():
    tok_data = xray.tokenizer.tokenize(prompt_text.strip())
    token_ids = tok_data.get("token_ids", [])
    clean_toks = [t.replace("\n", "↵") for t in tok_data.get("clean_tokens", [])]


# ── The 7 Tabs (Selected Visualization Interface) ──────────────────────────────
if prompt_text.strip():
    t_chat, t_tok, t_emb, t_attn, t_lay, t_log, t_gen = st.tabs([
        "💬 Chat", "🔤 Tokens", "🧭 Embeddings",
        "🧠 Attention", "🏗️ Layers", "📊 Logits", "🔄 Generation"
    ])

    # 1. 💬 Chat Tab ──────────────────────────────────────────────────────────
    with t_chat:
        st.markdown(
            '<div class="pipeline-flow">💬 User Prompt ➔ 🧠 Autoregressive LLM Inference ➔ 💬 Formatted Output Response</div>',
            unsafe_allow_html=True
        )
        curr_resp = st.session_state.get("response_text", "")
        if curr_resp:
            st.markdown(f"""
<div class="xray-response-box">
  <div class="xray-response-label">Response :</div>
  <div class="xray-response-text">{curr_resp}</div>
</div>
""", unsafe_allow_html=True)
            
            m1, m2, m3, m4 = st.columns(4)
            m1.caption(f"**Temperature:** `{opt_temp}`")
            m2.caption(f"**Top-K:** `{opt_top_k}`")
            m3.caption(f"**Top-P:** `{opt_top_p}`")
            m4.caption(f"**Max Tokens:** `{opt_max_tokens}`")
        else:
            st.info("Press **⚡ Generate** to generate a live model response.")

    # 2. 🔤 Tokens Tab ─────────────────────────────────────────────────────────
    with t_tok:
        st.markdown(
            '<div class="pipeline-flow">Input ➔ Tokenizer (AutoTokenizer) ➔ Tokens ➔ Token IDs</div>',
            unsafe_allow_html=True
        )
        
        st.markdown("**Input Prompt:**")
        st.code(prompt_text.strip(), language="text")

        st.markdown(f"**Tokens ({len(clean_toks)}):**")
        st.markdown(" ".join(f'<span class="tok-chip">{t}</span>' for t in clean_toks), unsafe_allow_html=True)

        st.markdown("**Token IDs:**")
        st.markdown(" ".join(f'<span class="tok-id-chip">{tid}</span>' for tid in token_ids), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📋 **Token Decomposition Table**")
        df_toks = pd.DataFrame({
            "Position": list(range(len(clean_toks))),
            "Token": clean_toks,
            "Token ID": token_ids,
            "Char Length": [len(t) for t in clean_toks],
            "Hex Bytes": [" ".join(f"0x{b:02X}" for b in t.encode("utf-8")) for t in clean_toks]
        })
        st.dataframe(df_toks, use_container_width=True, hide_index=True)

        with st.expander("🏷️ Visual Token Segmentation & Colors"):
            st.markdown(xray.tokenizer.get_colored_html(prompt_text.strip()), unsafe_allow_html=True)

        with st.expander("🔍 Vocabulary Token Lookup"):
            lookup_q = st.text_input("Search vocabulary by token string or integer ID:", value="Machine", key="tok_lookup_q")
            if lookup_q.strip():
                res_lookup = xray.tokenizer.inspect_token(lookup_q.strip())
                st.json(res_lookup)

    # 3. 🧭 Embeddings Tab ─────────────────────────────────────────────────────
    with t_emb:
        st.markdown(
            '<div class="pipeline-flow">Token ➔ Token ID ➔ Embedding Vector (d_model)</div>',
            unsafe_allow_html=True
        )

        with st.spinner("Extracting input embedding representations..."):
            embed_data = cached_embeddings(tuple(token_ids))
        
        embed_matrix = embed_data["embeddings"]
        embed_dim    = embed_data["embedding_dim"]
        stats_list   = embed_data["stats"]

        st.markdown(f"**Embedding Dimension ($d_{{model}}$):** `{embed_dim}`")

        if stats_list:
            st.markdown("#### 📊 **Vector Statistics per Token**")
            df_embed = pd.DataFrame([
                {
                    "Token": s["token_str"],
                    "Token ID": s["token_id"],
                    "L2 Norm (||v||)": f"{s['norm']:.4f}",
                    "Mean (μ)": f"{s['mean']:.4f}",
                    "Std (σ)": f"{s['std']:.4f}",
                    "Min": f"{s['min']:.4f}",
                    "Max": f"{s['max']:.4f}",
                    "Vector Preview": s["preview"]
                }
                for s in stats_list
            ])
            st.dataframe(df_embed, use_container_width=True, hide_index=True)

            with st.expander("🔍 Raw Vector Inspector"):
                sel_idx = st.selectbox(
                    "Select Token to View Raw Embedding Values:",
                    range(len(stats_list)),
                    format_func=lambda i: f"[{i}] '{stats_list[i]['token_str']}' (ID: {stats_list[i]['token_id']})",
                    key="raw_embed_select"
                )
                raw_v = stats_list[sel_idx]["vector"]
                st.json({
                    "token": stats_list[sel_idx]["token_str"],
                    "token_id": stats_list[sel_idx]["token_id"],
                    "dimension": embed_dim,
                    "first_32_values": [round(float(x), 5) for x in raw_v[:32]],
                    "full_dimension_count": len(raw_v)
                })

        if len(clean_toks) >= 1:
            st.markdown("#### 🗺️ **2D Embedding Space (PCA Projection)**")
            st.plotly_chart(plot_embedding_pca_2d(clean_toks, token_ids, embed_matrix), use_container_width=True)

    # 4. 🧠 Attention Tab ──────────────────────────────────────────────────────
    with t_attn:
        st.markdown(
            '<div class="pipeline-flow">Q · Kᵀ / √d_k ➔ Softmax ➔ Multi-Head Self-Attention Weights</div>',
            unsafe_allow_html=True
        )

        c_l, c_h = st.columns(2)
        with c_l:
            attn_layer = st.number_input(
                "Transformer Layer:",
                min_value=1,
                max_value=num_layers,
                value=int(opt_layer),
                key="tab_attn_layer"
            )
        with c_h:
            attn_head = st.number_input(
                "Attention Head:",
                min_value=1,
                max_value=num_heads,
                value=int(opt_head),
                key="tab_attn_head"
            )

        l_idx = int(attn_layer) - 1
        h_idx = int(attn_head) - 1

        with st.spinner("Extracting attention weights..."):
            attn_res = cached_inspect(prompt_text.strip(), top_k=int(opt_top_k))

        if attn_res and attn_res.get("seq_len", 0) > 0:
            attentions = attn_res.get("attentions")
            if attentions is not None and attentions.ndim == 4:
                mat = attentions[l_idx, h_idx]

                st.markdown(f"#### 📊 **Attention Matrix (ASCII Representation — Layer {attn_layer}, Head {attn_head})**")
                st.code(generate_ascii_attention_matrix(clean_toks, mat), language="text")

                st.markdown(f"#### 🔥 **Interactive Attention Heatmap (Layer {attn_layer}, Head {attn_head})**")
                st.plotly_chart(
                    plot_attention_heatmap(clean_toks, mat, int(attn_layer), int(attn_head)),
                    use_container_width=True
                )

                with st.expander(f"🧩 Multi-Head Grid Overview (Layer {attn_layer} — All {num_heads} Heads)", expanded=False):
                    st.plotly_chart(
                        plot_multi_head_grid(clean_toks, attentions[l_idx], int(attn_layer)),
                        use_container_width=True
                    )

                if attn_res.get("rollout_matrix") is not None:
                    with st.expander("🌀 Attention Rollout (Global Information Flow Across All Layers)", expanded=False):
                        st.plotly_chart(
                            plot_attention_rollout(clean_toks, attn_res["rollout_matrix"]),
                            use_container_width=True
                        )

    # 5. 🏗️ Layers Tab ─────────────────────────────────────────────────────────
    with t_lay:
        st.markdown(
            '<div class="pipeline-flow">Embeddings ➔ Layer 1 ➔ Layer 2 ➔ ... ➔ Layer N ➔ Final Output</div>',
            unsafe_allow_html=True
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Layers", num_layers)
        m2.metric("Attention Heads", f"{num_heads} heads")
        m3.metric("Hidden Dim (d_model)", d_model)
        m4.metric("MLP Dim (d_ff)", d_ff)

        with st.expander(f"🔬 Explore Transformer Block Architecture ({num_layers} Blocks)", expanded=False):
            sel_block = st.slider("Select Transformer Block #:", 1, num_layers, 1, key="block_slider")
            st.markdown(f"""
- **1. Pre-Attention Normalization:** `{norm_type}` (dimension = `{d_model}`)
- **2. Multi-Head Self-Attention:** `{num_heads} heads` $\\times$ `{head_dim} dims/head` | Positional Encoding: `{model_info.get('pos_emb', 'RoPE')}`
- **3. Residual Connection:** $x = x + \\text{{Attention}}(x)$
- **4. Pre-MLP Normalization:** `{norm_type}` (dimension = `{d_model}`)
- **5. Feed-Forward MLP:** $\\mathbb{{R}}^{{{d_model}}} \\to \\mathbb{{R}}^{{{d_ff}}} \\to \\mathbb{{R}}^{{{d_model}}}$
- **6. Residual Connection:** $x = x + \\text{{MLP}}(x)$
""")

        st.markdown("---")
        st.markdown("#### 🧬 **Hidden States Extraction**")
        st.markdown("Select layers to extract and inspect hidden state representations:")

        PRESET_LAYERS = [1, min(10, num_layers), min(20, num_layers), num_layers]
        PRESET_LAYERS = sorted(list(set(PRESET_LAYERS)))
        cols_hs = st.columns(len(PRESET_LAYERS))
        selected_hs = []
        for ci, ln in enumerate(PRESET_LAYERS):
            if cols_hs[ci].checkbox(f"Layer {ln}", value=(ln == 1), key=f"hs_tab_ck_{ln}"):
                selected_hs.append(ln)

        show_pca_hs = st.toggle("📊 2D PCA Scatter for Hidden States", value=True, key="hs_tab_pca_toggle")

        if selected_hs:
            with st.spinner("Extracting hidden states across layers..."):
                hsd = cached_hidden_states(tuple(token_ids))
            all_hs = hsd.get("hidden_states", [])
            hs_lbl = hsd.get("layer_labels", [])

            for ln in selected_hs:
                hs_idx = min(ln, len(all_hs) - 1)
                hs_arr = all_hs[hs_idx]
                label_txt = hs_lbl[hs_idx] if hs_idx < len(hs_lbl) else f"Layer {ln}"
                
                st.markdown(f"##### 🔷 **{label_txt}** — Hidden State Vector Stats")
                rows = [
                    {
                        "Token #": ti,
                        "Token": clean_toks[ti],
                        "L2 Norm": f"{float(np.linalg.norm(hs_arr[ti])):.4f}",
                        "Mean": f"{float(np.mean(hs_arr[ti])):.4f}",
                        "Std": f"{float(np.std(hs_arr[ti])):.4f}",
                        "Min": f"{float(np.min(hs_arr[ti])):.4f}",
                        "Max": f"{float(np.max(hs_arr[ti])):.4f}",
                        "Preview": "[" + ", ".join(f"{x:+.3f}" for x in hs_arr[ti][:4]) + ", …]"
                    }
                    for ti in range(len(clean_toks))
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                if show_pca_hs and len(clean_toks) >= 2:
                    st.plotly_chart(
                        plot_hidden_state_pca(clean_toks, hs_arr, label_txt, color_seed=ln),
                        use_container_width=True
                    )
        else:
            st.info("Select at least one layer checkbox above to inspect hidden states.")

        # Residual Dynamics and MLP summary
        insp_data = cached_inspect(prompt_text.strip(), top_k=5)
        
        if insp_data.get("residual_dynamics"):
            with st.expander("📈 Residual Stream Dynamics (L2 Growth & Cosine Drift)", expanded=False):
                fig_norm, fig_drift = plot_residual_stream_dynamics(insp_data["residual_dynamics"], clean_toks)
                st.plotly_chart(fig_norm, use_container_width=True)
                st.plotly_chart(fig_drift, use_container_width=True)

        if insp_data.get("mlp_summary"):
            with st.expander("⚡ MLP Neuron Sparsity & Activations", expanded=False):
                st.plotly_chart(
                    plot_neuron_sparsity(insp_data["mlp_summary"]),
                    use_container_width=True
                )

    # 6. 📊 Logits Tab ─────────────────────────────────────────────────────────
    with t_log:
        st.markdown(
            '<div class="pipeline-flow">Hidden State ➔ LM Head ➔ Logits ➔ Softmax ➔ Next-Token Probabilities</div>',
            unsafe_allow_html=True
        )

        top_k_log = st.slider(
            "Top-K Next Tokens to Display:",
            min_value=3,
            max_value=30,
            value=min(int(opt_top_k), 30),
            key="tab_logits_topk"
        )

        with st.spinner("Computing next token logits and probability distribution..."):
            logit_res = cached_inspect(prompt_text.strip(), top_k=int(top_k_log))

        if logit_res and logit_res.get("top_next_tokens"):
            top_pairs = logit_res["top_next_tokens"]
            t_toks = [t for t, _ in top_pairs]
            t_probs = [p for _, p in top_pairs]

            st.markdown("#### 📋 **Top Next-Token Predictions**")
            df_top_log = pd.DataFrame({
                "Rank": [f"#{i+1}" for i in range(len(top_pairs))],
                "Token": [f"'{t}'" for t in t_toks],
                "Probability": [f"{p*100:.2f}%" for p in t_probs],
                "Raw Value": [round(p, 6) for p in t_probs]
            })
            st.dataframe(df_top_log, use_container_width=True, hide_index=True)

            st.markdown("#### 📊 **Next-Token Probability Distribution**")
            st.plotly_chart(
                plot_top_logits_probabilities(t_toks, t_probs, top_k=int(top_k_log)),
                use_container_width=True
            )

            ent_val = logit_res.get("entropy", 0.0)
            confidence_badge = "High Confidence (Low Entropy)" if ent_val < 2.5 else "Moderate / High Uncertainty"
            st.markdown(f"**Model Entropy:** `{ent_val:.3f} nats` — *{confidence_badge}*")

            if logit_res.get("logit_lens"):
                with st.expander("🔭 Logit Lens (Early Un-embedding Layer Progression)", expanded=False):
                    st.plotly_chart(
                        plot_logit_lens_matrix(clean_toks, logit_res["logit_lens"]),
                        use_container_width=True
                    )

    # 7. 🔄 Generation Tab ─────────────────────────────────────────────────────
    with t_gen:
        st.markdown(
            '<div class="pipeline-flow">Prompt ➔ Token 1 ➔ Token 2 ➔ Token 3 ➔ ... ➔ Final Autoregressive Text</div>',
            unsafe_allow_html=True
        )

        c_g1, c_g2 = st.columns([3, 1.5])
        with c_g1:
            gen_steps = st.slider(
                "Number of tokens to trace step by step:",
                min_value=3,
                max_value=25,
                value=min(int(opt_max_tokens), 12),
                key="gen_tab_step_slider"
            )
        with c_g2:
            st.write("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            run_step_btn = st.button("▶ Run Step-by-Step", key="run_step_by_step_btn", use_container_width=True, type="primary")

        if run_step_btn:
            with st.spinner("Generating autoregressive tokens one by one..."):
                gen_hist = xray.generate_step_by_step(
                    prompt_text.strip(),
                    max_new_tokens=int(gen_steps),
                    top_k=int(opt_top_k)
                )
                st.session_state["gen_history"] = gen_hist

        hist = st.session_state.get("gen_history", [])
        if hist:
            st.markdown("#### 📜 **Incremental Generation Progression**")
            st.markdown(f"**Prompt:** `{prompt_text.strip()}`")
            for h in hist:
                st.markdown(f"➔ `{h['full_text']}`")

            st.markdown("---")
            st.markdown("#### 📊 **Per-Step Token Diagnostics**")
            rows_gen = [
                {
                    "Step": f"Step {h['step']}",
                    "Generated Token": f"'{h['generated_token']}'",
                    "Token ID": h.get("generated_id", "—"),
                    "Confidence": f"{h['confidence']*100:.2f}%",
                    "Entropy (nats)": f"{h['entropy']:.3f}",
                    "Alternative Top Candidates": " | ".join(
                        f"'{t}' {p*100:.1f}%" for t, p in h.get("top_candidates", [])[1:4]
                    ) or "—"
                }
                for h in hist
            ]
            st.dataframe(pd.DataFrame(rows_gen), use_container_width=True, hide_index=True)

            st.markdown("#### ✅ **Generated Full Text Output**")
            st.success(f"**{hist[-1]['full_text']}**")
        else:
            st.info("Press **▶ Run Step-by-Step** to trace step-by-step autoregressive generation.")

else:
    st.info("Enter a prompt above and press **⚡ Generate** to begin exploring.")


# ── Response Box at Bottom (Matching Wireframe) ───────────────────────────────
resp_text_display = st.session_state.get("response_text", "")
if resp_text_display:
    st.markdown(f"""
<div class="xray-response-box">
  <div class="xray-response-label">Response :</div>
  <div class="xray-response-text">{resp_text_display}</div>
</div>
""", unsafe_allow_html=True)
