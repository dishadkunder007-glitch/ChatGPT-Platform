"""
LocalGPT — Full-Feature ChatGPT-Style Local AI Assistant with LLM X-Ray & RAG
Features:
  • Header: LOCALGPT Branding + Model Badge + Settings Drawer Toggle
  • Sidebar: + New Chat, Categorized History (Today, Previous 7 Days, Older), Document Knowledge Base (Upload PDF/TXT/DOCX), Generation Controls, System Instructions
  • Multi-turn conversation with ContextBuilder pipeline & SQLite persistence
  • Word-by-word streaming with blinking cursor
  • Message controls: Copy, Regenerate, and inline X-Ray
  • Full Mechanistic Interpretability X-Ray (5 Tabs):
      1. Tokens: sub-word tokens, IDs, whitespace representation, breakdown table
      2. Embeddings: 2D PCA vector space trajectory & dense stats table
      3. Attention: Interactive heatmaps, multi-head grid, ASCII matrix, rollout
      4. Logits: Next-token predictions, ASCII & HTML probability bars, logit lens
      5. Token Generation: Confidence vs. Entropy autoregressive timeline & step-by-step token observer
  • Document Chat (RAG): PDF / TXT / DOCX upload + page-grounded Q&A + rich citation cards
"""

import os, sys, time, json, pyperclip, importlib
from datetime import datetime, timezone
import streamlit as st

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import xray
importlib.reload(xray)

from model        import XRayModel
from database     import LocalGPTDatabase
from memory       import MemoryManager
from embeddings   import EmbeddingEngine
from vector_store import FAISSVectorStore, VectorStore
from rag          import RAGPipeline
from chat         import ChatEngine
from xray         import XRayEngine
from visualization import (
    plot_attention_heatmap,
    plot_multi_head_grid,
    plot_attention_rollout,
    plot_logit_lens_matrix,
    plot_residual_stream_dynamics,
    plot_top_logits_probabilities,
    plot_generation_timeline,
    plot_neuron_sparsity,
    plot_embedding_pca_2d,
    plot_hidden_state_pca,
    generate_ascii_attention_matrix,
    generate_token_probability_bars,
    render_token_probability_html,
    DARK_LAYOUT
)

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LocalGPT",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom Stylesheet ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

/* ── App Background ── */
.stApp { background: #0b0f17; color: #e6edf3; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #06090e !important;
    border-right: 1px solid #1f242c !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem !important; }

/* ── Top App Bar ── */
.app-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: rgba(11, 15, 23, 0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #1f242c;
    position: sticky;
    top: 0;
    z-index: 999;
    margin: -1rem -1rem 1.2rem -1rem;
}
.brand-title {
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: 0.8px;
    background: linear-gradient(135deg, #58a6ff 0%, #38bdf8 50%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: flex;
    align-items: center;
    gap: 8px;
}
.header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
}
.model-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.76rem;
    font-weight: 500;
    padding: 4px 12px;
    border-radius: 20px;
    background: rgba(56, 189, 248, 0.08);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.25);
    font-family: 'JetBrains Mono', monospace;
}
.live-indicator {
    width: 7px;
    height: 7px;
    background: #3fb950;
    border-radius: 50%;
    box-shadow: 0 0 8px #3fb950;
}

/* ── Sidebar Sections ── */
.sb-brand {
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #58a6ff;
    padding: 10px 14px 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #1f242c;
    margin-bottom: 12px;
}
.sb-group-header {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8b949e;
    padding: 10px 12px 4px;
}

/* ── Chat Cards in Sidebar ── */
.chat-item {
    padding: 8px 10px;
    margin: 2px 4px;
    border-radius: 8px;
    border: 1px solid transparent;
    transition: all 0.15s ease;
    background: transparent;
}
.chat-item:hover { background: #161b22; border-color: #30363d; }
.chat-item.active { background: #182333; border-color: #388bfd66; }
.chat-item-title {
    font-size: 0.85rem;
    font-weight: 500;
    color: #e6edf3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.chat-item.active .chat-item-title { color: #58a6ff; font-weight: 600; }
.chat-item-meta {
    font-size: 0.70rem;
    color: #6e7681;
    margin-top: 2px;
    display: flex;
    gap: 8px;
}

/* ── Welcome Container ── */
.welcome-hero {
    text-align: center;
    padding: 50px 20px 30px;
}
.welcome-icon-box {
    font-size: 2.8rem;
    margin-bottom: 12px;
    filter: drop-shadow(0 0 16px rgba(88, 166, 255, 0.3));
}
.welcome-heading {
    font-size: 2rem;
    font-weight: 800;
    color: #f0f6fc;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
}
.welcome-subtext {
    font-size: 0.95rem;
    color: #8b949e;
    max-width: 480px;
    margin: 0 auto 28px;
    line-height: 1.5;
}

/* ── Streaming Animation ── */
@keyframes cursor-pulse { 0%,100%{opacity:1} 50%{opacity:0} }
.streaming-cursor {
    display: inline-block;
    width: 2px;
    height: 1.1em;
    background: #58a6ff;
    vertical-align: middle;
    animation: cursor-pulse 0.9s infinite;
    margin-left: 3px;
    border-radius: 1px;
}
.streaming-text {
    line-height: 1.7;
    font-size: 0.94rem;
    color: #e6edf3;
}

/* ── Inline Action Row ── */
.action-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
}

/* ── Document Citation Cards ── */
.citation-card {
    background: #0d121c;
    border: 1px solid #232d3d;
    border-left: 3px solid #38bdf8;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0 10px;
    font-size: 0.84rem;
}
.citation-head {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 4px;
}
.badge-page {
    font-size: 0.70rem;
    padding: 2px 8px;
    border-radius: 12px;
    background: rgba(63, 185, 80, 0.12);
    color: #3fb950;
    border: 1px solid rgba(63, 185, 80, 0.3);
    font-family: 'JetBrains Mono', monospace;
}
.badge-score {
    font-size: 0.70rem;
    padding: 2px 8px;
    border-radius: 12px;
    background: rgba(240, 136, 62, 0.12);
    color: #f0883e;
    border: 1px solid rgba(240, 136, 62, 0.3);
    font-family: 'JetBrains Mono', monospace;
}
.citation-body {
    color: #8b949e;
    font-style: italic;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid #1f242c;
    line-height: 1.5;
}

/* ── X-Ray Interactive Panel ── */
.xray-panel-wrap {
    background: #0d121c;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 14px 0 10px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.xray-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #1f242c;
    padding-bottom: 10px;
    margin-bottom: 12px;
}
.xray-title-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 14px;
    background: rgba(167, 139, 250, 0.15);
    color: #c4b5fd;
    border: 1px solid rgba(167, 139, 250, 0.35);
}
.xray-subtext {
    font-size: 0.76rem;
    color: #8b949e;
    font-family: 'JetBrains Mono', monospace;
}

.token-chip-badge {
    display: inline-block;
    padding: 6px 12px;
    margin: 4px 4px;
    border-radius: 8px;
    background: #141f2f;
    border: 1px solid #388bfd55;
    color: #58a6ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.86rem;
    font-weight: 500;
    transition: all 0.15s;
}
.token-chip-badge:hover {
    background: #1b2f4a;
    border-color: #38bdf8;
}
.token-chip-id {
    font-size: 0.65rem;
    color: #8b949e;
    display: block;
    text-align: center;
    margin-top: 2px;
}

/* ── Streamlit UI Tweaks ── */
div[data-testid="stChatInput"] textarea {
    background: #161b22 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
    font-size: 0.92rem !important;
}
div[data-testid="stChatMessage"] { background: transparent !important; }
/* ── Modern Vibrant Blue Buttons ── */
button[data-testid="stBaseButton-primary"],
div.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 50%, #3b82f6 100%) !important;
    color: #ffffff !important;
    border: 1px solid #60a5fa !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
    transition: all 0.2s ease-in-out !important;
}
button[data-testid="stBaseButton-primary"]:hover,
div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb 0%, #3b82f6 50%, #60a5fa 100%) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.55) !important;
    transform: translateY(-1px);
}

/* Secondary & Standard Buttons (Styled in sleek blue accents) */
button[data-testid="stBaseButton-secondary"],
div.stButton > button,
div.stDownloadButton > button {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
    color: #93c5fd !important;
    border: 1px solid rgba(59, 130, 246, 0.5) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease-in-out !important;
}
button[data-testid="stBaseButton-secondary"]:hover,
div.stButton > button:hover,
div.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border-color: #60a5fa !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
    transform: translateY(-1px);
}

div[data-testid="stExpander"] {
    background: #0e131d !important;
    border: 1px solid #232d3d !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Cached Singletons ────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _db():   return LocalGPTDatabase()

@st.cache_resource(show_spinner=False)
def _model(name):  return XRayModel(model_name=name)

@st.cache_resource(show_spinner=False)
def _emb():  return EmbeddingEngine()

@st.cache_resource(show_spinner=False)
def _vs():   return FAISSVectorStore()

@st.cache_resource(show_spinner=False)
def _rag(_e, _v, _d): return RAGPipeline(embedding_engine=_e, vector_store=_v, database=_d)

db  = _db()
emb = _emb()
vs  = _vs()
rag = _rag(emb, vs, db)

SUPPORTED_MODELS = getattr(XRayModel, "SUPPORTED_MODELS", [
    "Qwen/Qwen2.5-1.5B-Instruct",
    "gpt2",
    "distilgpt2",
    "gpt2-medium",
    "facebook/opt-125m",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
])
DEFAULT_SYSTEM_PROMPT = (
    "You are LocalGPT, a helpful, precise, and privacy-preserving AI assistant.\n"
    "Explain concepts clearly with examples when helpful."
)

# ─── Session State Initialization ─────────────────────────────────────────────
def _boot_session():
    sessions = db.get_sessions()
    if not sessions:
        sid = f"chat_{int(time.time()*1000)}"
        db.create_session(sid, title="New Chat", system_prompt=DEFAULT_SYSTEM_PROMPT)
        sessions = db.get_sessions()

    ss = st.session_state
    ss.setdefault("current_sid",         sessions[0]["session_id"])
    ss.setdefault("model_name",          "Qwen/Qwen2.5-1.5B-Instruct")
    ss.setdefault("temperature",         0.7)
    ss.setdefault("top_k",               50)
    ss.setdefault("top_p",               0.9)
    ss.setdefault("max_tokens",          180)
    ss.setdefault("stream_ms",           30)
    ss.setdefault("use_rag",             True)
    ss.setdefault("system_prompt",       DEFAULT_SYSTEM_PROMPT)
    ss.setdefault("show_settings",       False)
    ss.setdefault("renaming_sid",        None)
    ss.setdefault("suggested_prompt",    None)
    ss.setdefault("editing_idx",         None)
    ss.setdefault("action_pending",      None)
    ss.setdefault("copy_ack",            {})
    ss.setdefault("active_xray_msg_idx", None)  # active X-Ray inspector message index
    ss.setdefault("xray_layer",          1)
    ss.setdefault("xray_head",           1)
    ss.setdefault("xray_top_k",          8)

_boot_session()
ss = st.session_state

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _rel_time(iso: str) -> str:
    try:
        dt  = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
        sec = (datetime.now(timezone.utc) - dt).total_seconds()
        if sec < 60:    return "just now"
        if sec < 3600:  return f"{int(sec/60)}m ago"
        if sec < 86400: return f"{int(sec/3600)}h ago"
        return dt.strftime("%b %d")
    except Exception:
        return ""

def _group_sessions_by_date(sessions_list):
    groups = {"Today": [], "Previous 7 Days": [], "Older": []}
    now = datetime.now(timezone.utc)
    for s in sessions_list:
        try:
            iso = s.get("updated_at") or s.get("created_at") or ""
            dt = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
            diff_days = (now.date() - dt.date()).days
            if diff_days <= 0:
                groups["Today"].append(s)
            elif diff_days <= 7:
                groups["Previous 7 Days"].append(s)
            else:
                groups["Older"].append(s)
        except Exception:
            groups["Today"].append(s)
    return {k: v for k, v in groups.items() if v}

def _new_chat():
    sid = f"chat_{int(time.time()*1000)}"
    db.create_session(sid, title="New Chat", system_prompt=ss["system_prompt"])
    ss["current_sid"]  = sid
    ss["renaming_sid"] = None
    ss["active_xray_msg_idx"] = None
    st.rerun()

def _bytes_label(b: int) -> str:
    if b < 1024:       return f"{b} B"
    if b < 1048576:    return f"{b/1024:.1f} KB"
    return f"{b/1048576:.1f} MB"


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sb-brand">⚡ LOCALGPT</div>', unsafe_allow_html=True)

    # ── New Chat Button ──
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        _new_chat()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Categorized Chat History (Today / Previous 7 Days / Older) ──
    all_sessions = db.get_sessions_with_counts()
    grouped_sessions = _group_sessions_by_date(all_sessions)

    for group_name, sess_list in grouped_sessions.items():
        st.markdown(f'<div class="sb-group-header">{group_name}</div>', unsafe_allow_html=True)
        for s in sess_list:
            sid     = s["session_id"]
            title   = s["title"] or "New Chat"
            n_msgs  = s.get("message_count", 0)
            updated = _rel_time(s.get("updated_at", ""))
            active  = (sid == ss["current_sid"])
            cls     = "chat-item active" if active else "chat-item"

            if ss["renaming_sid"] == sid:
                new_name = st.text_input("", value=title, key=f"ri_{sid}", label_visibility="collapsed")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✓ Save", key=f"rs_{sid}", use_container_width=True):
                        if new_name.strip():
                            db.rename_session(sid, new_name.strip())
                        ss["renaming_sid"] = None
                        st.rerun()
                with c2:
                    if st.button("✕", key=f"rc_{sid}", use_container_width=True):
                        ss["renaming_sid"] = None
                        st.rerun()
                continue

            col_card, col_ren, col_del = st.columns([5, 0.6, 0.6])
            with col_card:
                st.markdown(f"""
<div class="{cls}">
  <div class="chat-item-title">{title}</div>
  <div class="chat-item-meta"><span>💬 {n_msgs}</span><span>🕐 {updated}</span></div>
</div>""", unsafe_allow_html=True)
                if st.button(" ", key=f"open_{sid}", use_container_width=True):
                    ss["current_sid"]  = sid
                    ss["renaming_sid"] = None
                    ss["editing_idx"]  = None
                    ss["active_xray_msg_idx"] = None
                    st.rerun()
            with col_ren:
                if st.button("✏️", key=f"ren_{sid}", help="Rename Chat"):
                    ss["renaming_sid"] = sid
                    st.rerun()
            with col_del:
                if st.button("🗑", key=f"del_{sid}", help="Delete Chat"):
                    db.delete_session(sid)
                    rest = db.get_sessions()
                    if rest:
                        ss["current_sid"] = rest[0]["session_id"]
                    else:
                        _new_chat()
                        break
                    st.rerun()

    # ── Document Knowledge Base (Upload PDF / TXT / DOCX) ──
    st.markdown("---")
    st.markdown('<div class="sb-group-header">📎 Document Knowledge Base</div>', unsafe_allow_html=True)
    
    with st.expander("📄 **Upload & Manage Files**", expanded=False):
        uploaded_files = st.file_uploader(
            "Upload PDF, TXT, DOCX",
            type=["pdf", "txt", "md", "docx", "csv", "json", "py"],
            accept_multiple_files=True,
            key="sb_doc_uploader"
        )
        if uploaded_files:
            if st.button("🚀 Index Document(s)", use_container_width=True, type="primary"):
                docs_dir = os.path.join(CURRENT_DIR, "data", "documents")
                os.makedirs(docs_dir, exist_ok=True)
                pbar = st.progress(0, text="Indexing file(s)...")
                for i, uf in enumerate(uploaded_files):
                    fpath = os.path.join(docs_dir, uf.name)
                    with open(fpath, "wb") as f:
                        f.write(uf.getbuffer())
                    res = rag.ingest_file(fpath)
                    pbar.progress((i + 1) / len(uploaded_files), text=f"Indexed {res['filename']} ({res['chunks_indexed']} chunks)")
                    st.toast(f"✅ Indexed {res['filename']}")
                pbar.empty()
                ss["use_rag"] = True
                st.rerun()

        # Indexed documents list
        docs = db.list_documents()
        vs_stats = vs.get_stats()
        if docs:
            st.markdown(f"<div style='font-size:0.75rem;color:#8b949e;margin:6px 0;'>Indexed: {len(docs)} documents ({vs_stats.get('total_chunks', 0)} chunks)</div>", unsafe_allow_html=True)
            for d in docs:
                dc1, dc2 = st.columns([4, 1])
                with dc1:
                    st.markdown(f"**📄 {d['filename']}**<br><span style='font-size:0.72rem;color:#6e7681;'>{d['file_type'].upper()} · {d['chunk_count']} chunks · {_bytes_label(d.get('file_size', 0))}</span>", unsafe_allow_html=True)
                with dc2:
                    if st.button("🗑", key=f"del_doc_{d['doc_id']}", help=f"Delete {d['filename']}"):
                        db.delete_document(d["doc_id"])
                        st.toast(f"Deleted {d['filename']}")
                        st.rerun()
        else:
            st.caption("No documents indexed yet. Upload a PDF above.")

    # ── Generation & Settings Shortcut in Sidebar ──
    with st.expander("⚙️ **Settings & Model**", expanded=False):
        chosen_model = st.selectbox(
            "Model",
            SUPPORTED_MODELS,
            index=SUPPORTED_MODELS.index(ss["model_name"]) if ss["model_name"] in SUPPORTED_MODELS else 0
        )
        if chosen_model != ss["model_name"]:
            ss["model_name"] = chosen_model
            st.rerun()

        ss["temperature"] = st.slider("Temperature", 0.0, 1.2, ss["temperature"], 0.05)
        ss["top_k"]       = st.slider("Top-K", 1, 200, ss["top_k"], 1)
        ss["top_p"]       = st.slider("Top-P", 0.1, 1.0, ss["top_p"], 0.05)
        ss["max_tokens"]  = st.slider("Max New Tokens", 32, 512, ss["max_tokens"], 16)
        ss["use_rag"]     = st.checkbox("Enable Document RAG", value=ss["use_rag"])

        st.markdown("<div style='font-size:0.75rem;color:#8b949e;margin-top:6px;'>System Instructions:</div>", unsafe_allow_html=True)
        sys_edit = st.text_area("System prompt", value=ss["system_prompt"], height=90, label_visibility="collapsed")
        if st.button("Save System Prompt", use_container_width=True):
            ss["system_prompt"] = sys_edit.strip() or DEFAULT_SYSTEM_PROMPT
            st.toast("System prompt saved ✅")
            st.rerun()


# ─── Load Model & Engines ─────────────────────────────────────────────────────
with st.spinner("Initializing LocalGPT engine…"):
    llm = _model(ss["model_name"])

memory      = MemoryManager(session_id=ss["current_sid"], db=db)
memory.system_prompt = ss["system_prompt"]
chat_engine = ChatEngine(model=llm, memory=memory, rag_pipeline=rag)
xray_engine = XRayEngine(model=llm)


# ─── Top Navigation Header ────────────────────────────────────────────────────
active_s   = db.get_session(ss["current_sid"]) or {}
chat_title = active_s.get("title", "LocalGPT")

h_col1, h_col2 = st.columns([6, 2])
with h_col1:
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;padding:6px 0;">
  <span class="brand-title">⚡ LOCALGPT</span>
  <span style="color:#6e7681;font-size:0.9rem;">/</span>
  <span style="font-weight:600;font-size:0.95rem;color:#e6edf3;">{chat_title}</span>
</div>
""", unsafe_allow_html=True)

with h_col2:
    btn_label = "⚙ Settings ▲" if ss.get("show_settings") else "⚙ Settings ▼"
    if st.button(btn_label, key="toggle_settings_btn", use_container_width=True):
        ss["show_settings"] = not ss.get("show_settings", False)
        st.rerun()

# ─── Expandable Top Settings Drawer ───────────────────────────────────────────
if ss.get("show_settings"):
    with st.container():
        st.markdown("""
<div style="background:#131b27;border:1px solid #232d3d;border-radius:10px;padding:16px 20px;margin-bottom:16px;">
  <div style="font-size:0.82rem;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:#38bdf8;margin-bottom:10px;">
    ⚙️ LocalGPT Configuration & Persona Controls
  </div>
</div>
""", unsafe_allow_html=True)
        s_c1, s_c2, s_c3 = st.columns([2, 2, 3])
        with s_c1:
            st.markdown("**LLM Engine**")
            sel_m = st.selectbox("Active Model", SUPPORTED_MODELS, index=SUPPORTED_MODELS.index(ss["model_name"]) if ss["model_name"] in SUPPORTED_MODELS else 0, key="top_model_sel")
            if sel_m != ss["model_name"]:
                ss["model_name"] = sel_m
                st.rerun()
            ss["use_rag"] = st.checkbox("📚 Enable Document RAG", value=ss["use_rag"], key="top_rag_cb")
        with s_c2:
            st.markdown("**Sampling Hyperparameters**")
            ss["temperature"] = st.slider("🌡 Temperature", 0.0, 1.2, ss["temperature"], 0.05, key="top_temp")
            ss["max_tokens"]  = st.slider("📏 Max New Tokens", 32, 512, ss["max_tokens"], 16, key="top_tokens")
        with s_c3:
            st.markdown("**System Persona Instructions**")
            top_sys = st.text_area("System prompt", value=ss["system_prompt"], height=75, key="top_sys_ta", label_visibility="collapsed")
            if st.button("Apply Settings", type="primary", use_container_width=True, key="top_apply_sys"):
                ss["system_prompt"] = top_sys.strip() or DEFAULT_SYSTEM_PROMPT
                st.toast("Settings updated successfully! ✅")
                st.rerun()
    st.markdown("---")


# ─── Handle Pending Actions (Regenerate / Edit) ───────────────────────────────
messages = memory.get_history()

if ss.get("action_pending"):
    action = ss.pop("action_pending")

    if action == "regenerate":
        with st.chat_message("assistant", avatar="⚡"):
            ph = st.empty()
            accumulated = ""
            for pkt in chat_engine.regenerate_last_response(
                temperature=ss["temperature"], top_p=ss["top_p"],
                top_k=ss["top_k"], max_new_tokens=ss["max_tokens"],
                use_rag=ss["use_rag"]
            ):
                accumulated = pkt.get("accumulated", accumulated)
                if not pkt.get("done"):
                    ph.markdown(f'<div class="streaming-text">{accumulated}<span class="streaming-cursor"></span></div>', unsafe_allow_html=True)
                    time.sleep(ss["stream_ms"] / 1000.0)
                else:
                    ph.markdown(accumulated)
        st.rerun()

    elif isinstance(action, tuple) and action[0] == "edit":
        _, edit_idx, new_text = action
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(f"*(edited)* {new_text}")
        with st.chat_message("assistant", avatar="⚡"):
            ph = st.empty()
            accumulated = ""
            for pkt in chat_engine.edit_and_resubmit(
                new_user_content=new_text, edit_turn_index=edit_idx,
                temperature=ss["temperature"], top_p=ss["top_p"],
                top_k=ss["top_k"], max_new_tokens=ss["max_tokens"],
                use_rag=ss["use_rag"]
            ):
                accumulated = pkt.get("accumulated", accumulated)
                if not pkt.get("done"):
                    ph.markdown(f'<div class="streaming-text">{accumulated}<span class="streaming-cursor"></span></div>', unsafe_allow_html=True)
                    time.sleep(ss["stream_ms"] / 1000.0)
                else:
                    ph.markdown(accumulated)
        st.rerun()


# ─── Conversation Thread ──────────────────────────────────────────────────────
messages = memory.get_history()

if not messages:
    # ── Welcome View ──
    st.markdown("""
<div class="welcome-hero">
  <div class="welcome-icon-box">⚡</div>
  <div class="welcome-heading">How can I help you today?</div>
  <div class="welcome-subtext">Multi-turn memory · Local private inference · Document Q&A · Mechanistic X-Ray</div>
</div>
""", unsafe_allow_html=True)

    SUGGESTIONS = [
        ("🤖 Explain Transformers",        "Explain Transformers"),
        ("💡 Explain with an example",      "Explain with an example"),
        ("🐍 Python Interview Questions",   "Give me 5 essential Python interview questions with explanations."),
        ("📄 Summarise My Documents",       "Summarise the key points from my uploaded documents."),
    ]
    s_col1, s_col2 = st.columns(2)
    s_cols = [s_col1, s_col2, s_col1, s_col2]
    for i, (label, prompt_text) in enumerate(SUGGESTIONS):
        with s_cols[i]:
            if st.button(label, key=f"sug_btn_{i}", use_container_width=True):
                ss["suggested_prompt"] = prompt_text
                st.rerun()

else:
    # ── Render Chat Message Turns ──
    for idx, msg in enumerate(messages):
        is_user = (msg.role == "user")
        avatar  = "🧑‍💻" if is_user else "⚡"

        with st.chat_message(msg.role, avatar=avatar):
            if is_user and ss.get("editing_idx") == idx:
                edit_val = st.text_area("Edit message", value=msg.content, key=f"edit_ta_{idx}", height=80, label_visibility="collapsed")
                ea, eb = st.columns(2)
                with ea:
                    if st.button("✓ Submit Edit", key=f"submit_edit_{idx}", use_container_width=True, type="primary"):
                        ss["editing_idx"]   = None
                        ss["action_pending"] = ("edit", idx, edit_val)
                        st.rerun()
                with eb:
                    if st.button("✕ Cancel", key=f"cancel_edit_{idx}", use_container_width=True):
                        ss["editing_idx"] = None
                        st.rerun()
            else:
                st.markdown(msg.content)

                # ── User Action Bar ──
                if is_user:
                    if st.button("✏️ Edit", key=f"edit_btn_{idx}", help="Edit this prompt"):
                        ss["editing_idx"] = idx
                        st.rerun()
                else:
                    # ── AI Action Bar: [Copy] [Regenerate] [🔬 X-Ray] ──
                    ac1, ac2, ac3, _ac_fill = st.columns([1.1, 1.3, 1.2, 5])
                    
                    with ac1:
                        copy_label = "✅ Copied!" if (time.time() - ss["copy_ack"].get(idx, 0) < 2) else "📋 Copy"
                        if st.button(copy_label, key=f"copy_{idx}", help="Copy response"):
                            try:
                                pyperclip.copy(msg.content)
                            except Exception:
                                pass
                            ss["copy_ack"][idx] = time.time()
                            st.rerun()

                    with ac2:
                        if idx == len(messages) - 1:
                            if st.button("🔄 Regenerate", key=f"regen_{idx}", help="Regenerate this response"):
                                ss["action_pending"] = "regenerate"
                                st.rerun()

                    with ac3:
                        xray_active = (ss.get("active_xray_msg_idx") == idx)
                        xray_btn_label = "🔬 Close X-Ray" if xray_active else "🔬 X-Ray"
                        if st.button(xray_btn_label, key=f"xray_btn_{idx}", help="Inspect internal transformer activations"):
                            ss["active_xray_msg_idx"] = None if xray_active else idx
                            st.rerun()

                    # ── RAG Grounded Sources ──
                    if msg.metadata.get("sources"):
                        srcs = msg.metadata["sources"]
                        with st.expander(f"📑 Sources  ({len(srcs)} reference{'s' if len(srcs) > 1 else ''})", expanded=True):
                            for s in srcs:
                                fname     = s.get("filename",   "Document")
                                page      = s.get("page_range", str(s.get("page_number", "?")))
                                tot_pages = s.get("total_pages", "?")
                                score     = s.get("similarity_score", 0)
                                preview   = s.get("preview", "")[:200]
                                st.markdown(f"""
<div class="citation-card">
  <div class="citation-head">
    <span>📄 {fname}</span>
    <span class="badge-page">📖 Page {page} / {tot_pages}</span>
    <span class="badge-score">🎯 {score}% match</span>
  </div>
  <div class="citation-body">"{preview}..."</div>
</div>""", unsafe_allow_html=True)

                    # ── Mechanistic Interpretability X-Ray Panel ──
                    if ss.get("active_xray_msg_idx") == idx:
                        prompt_to_inspect = messages[idx - 1].content if idx > 0 else msg.content
                        
                        st.markdown("""
<div class="xray-panel-wrap">
  <div class="xray-panel-head">
    <span class="xray-title-pill">🔬 LLM X-Ray Inspection Panel</span>
    <span class="xray-subtext">Tokens → Embeddings → Attention → Logits → Token Generation</span>
  </div>
</div>
""", unsafe_allow_html=True)

                        with st.spinner("Extracting internal representations..."):
                            xd = xray_engine.get_full_xray_data(prompt_to_inspect, top_k=ss["xray_top_k"])

                        tokens   = xd.get("tokens", [])
                        tok_ids  = xd.get("token_ids", [])
                        n_layers = xd.get("num_layers", 12)
                        n_heads  = xd.get("num_heads", 12)

                        tab_tok, tab_emb, tab_attn, tab_logits, tab_gen = st.tabs([
                            "🔤 Tokens",
                            "🧭 Embeddings",
                            "🧩 Attention",
                            "📊 Logits & Probabilities",
                            "⚡ Token Generation"
                        ])

                        # ── Tab 1: Tokens (Step 11) ──
                        with tab_tok:
                            st.markdown(f"**Sub-Word Token Breakdown** · `{len(tokens)}` tokens identified")
                            if tokens:
                                chip_html = ""
                                for tok, tid in zip(tokens, tok_ids):
                                    disp = tok.replace(" ", "·").replace("\n", "↵")
                                    chip_html += f"<span class='token-chip-badge'>{disp}<span class='token-chip-id'>ID {tid}</span></span>"
                                st.markdown(f"<div style='padding:8px 0;'>{chip_html}</div>", unsafe_allow_html=True)

                                import pandas as pd
                                tok_df = pd.DataFrame({
                                    "Index": range(len(tokens)),
                                    "Token": tokens,
                                    "Visible Token": [t.replace(" ", "·").replace("\n", "↵") for t in tokens],
                                    "Token ID": tok_ids,
                                    "Length (Chars)": [len(t) for t in tokens]
                                })
                                st.dataframe(tok_df, use_container_width=True, hide_index=True)

                        # ── Tab 2: Embeddings (Step 12) ──
                        with tab_emb:
                            st.markdown("**Token Embedding Space (Dense Numerical Representations)**")
                            if xd.get("embeddings") is not None:
                                try:
                                    fig_emb = xray_engine.generate_embedding_pca(prompt_to_inspect)
                                    if fig_emb:
                                        st.plotly_chart(fig_emb, use_container_width=True)
                                except Exception:
                                    pass

                            if xd.get("emb_stats"):
                                import pandas as pd
                                st.markdown("**Embedding Vector Properties & Statistics**")
                                st.dataframe(pd.DataFrame(xd["emb_stats"]), use_container_width=True, hide_index=True)

                        # ── Tab 3: Attention (Step 13) ──
                        with tab_attn:
                            st.markdown("**Self-Attention Mechanism (Query vs. Key Weightings)**")
                            
                            ac_c1, ac_c2 = st.columns(2)
                            with ac_c1:
                                ss["xray_layer"] = st.slider("Layer", 1, max(1, n_layers), ss["xray_layer"], 1, key=f"attn_layer_{idx}")
                            with ac_c2:
                                ss["xray_head"] = st.slider("Attention Head", 1, max(1, n_heads), ss["xray_head"], 1, key=f"attn_head_{idx}")

                            try:
                                fig_attn = xray_engine.generate_attention_heatmap(prompt_to_inspect, layer=ss["xray_layer"], head=ss["xray_head"])
                                if fig_attn:
                                    st.plotly_chart(fig_attn, use_container_width=True)
                            except Exception:
                                pass

                            if xd.get("ascii_attn"):
                                with st.expander("📄 ASCII Block Attention Matrix", expanded=False):
                                    st.code(xd["ascii_attn"], language=None)

                            try:
                                fig_grid = xray_engine.generate_multi_head_grid(prompt_to_inspect, layer=ss["xray_layer"])
                                if fig_grid:
                                    with st.expander(f"🧩 Multi-Head Overview — Layer {ss['xray_layer']} ({n_heads} Heads)", expanded=False):
                                        st.plotly_chart(fig_grid, use_container_width=True)
                            except Exception:
                                pass

                            try:
                                fig_roll = xray_engine.generate_attention_rollout(prompt_to_inspect)
                                if fig_roll:
                                    with st.expander("🌊 Attention Rollout (All Layers Aggregated)", expanded=False):
                                        st.plotly_chart(fig_roll, use_container_width=True)
                            except Exception:
                                pass

                        # ── Tab 4: Logits & Probabilities (Step 14) ──
                        with tab_logits:
                            st.markdown("**Next-Token Logits & Softmax Probability Distribution**")
                            
                            # ASCII Probability Bars
                            if xd.get("ascii_prob_bars"):
                                st.code(xd["ascii_prob_bars"], language=None)

                            # Interactive HTML Bar Widget
                            if xd.get("html_prob_bars"):
                                st.markdown(xd["html_prob_bars"], unsafe_allow_html=True)

                            # Plotly Distribution
                            if xd.get("top_tokens") and xd.get("top_probs"):
                                try:
                                    fig_logits = plot_top_logits_probabilities(xd["top_tokens"], xd["top_probs"], top_k=ss["xray_top_k"])
                                    if fig_logits:
                                        st.plotly_chart(fig_logits, use_container_width=True)
                                except Exception:
                                    pass

                            # Logit Lens
                            try:
                                fig_lens = xray_engine.generate_logit_lens(prompt_to_inspect, top_k=5)
                                if fig_lens:
                                    with st.expander("🔭 Logit Lens (Layer-by-Layer Intermediate Predictions)", expanded=False):
                                        st.plotly_chart(fig_lens, use_container_width=True)
                            except Exception:
                                pass

                        # ── Tab 5: Token Generation Dynamics (Step 15) ──
                        with tab_gen:
                            st.markdown("**Autoregressive Token Generation Dynamics (Step-by-Step Evolution)**")
                            
                            gen_hist = xd.get("generation_history", [])
                            if gen_hist:
                                # Confidence & Entropy Timeline Chart
                                fig_timeline = plot_generation_timeline(gen_hist)
                                if fig_timeline:
                                    st.plotly_chart(fig_timeline, use_container_width=True)

                                # Step-by-Step Data Table
                                import pandas as pd
                                rows = []
                                for step_item in gen_hist:
                                    top_c = step_item.get("top_candidates", [])
                                    cand_str = ", ".join([f"'{c[0]}' ({c[1]*100:.1f}%)" for c in top_c[:3]])
                                    rows.append({
                                        "Step": step_item.get("step"),
                                        "Generated Token": step_item.get("generated_token"),
                                        "Token ID": step_item.get("generated_id"),
                                        "Confidence (%)": f"{step_item.get('confidence', 0)*100:.1f}%",
                                        "Entropy (nats)": f"{step_item.get('entropy', 0):.3f}",
                                        "Top Candidates": cand_str
                                    })
                                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                            # Interactive Autoregressive Stepper
                            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                            with st.expander("⚡ **Live Autoregressive Stepper Simulator**", expanded=False):
                                step_count = st.slider("Number of Generation Steps to Trace", 2, 16, 6, key=f"sim_steps_{idx}")
                                if st.button("▶ Run Step-by-Step Trace", key=f"btn_step_sim_{idx}"):
                                    with st.spinner("Simulating autoregressive generation..."):
                                        sim_hist = llm.generate_step_by_step(prompt_to_inspect, max_new_tokens=step_count, top_k=5)
                                        if sim_hist:
                                            fig_sim = plot_generation_timeline(sim_hist)
                                            if fig_sim:
                                                st.plotly_chart(fig_sim, use_container_width=True)
                                            for h in sim_hist:
                                                st.markdown(f"**Step {h['step']}:** `{h['generated_token']}` · *Confidence:* `{h['confidence']*100:.1f}%` · *Entropy:* `{h['entropy']:.3f}`")


# ─── Chat Input Bar ───────────────────────────────────────────────────────────
pending_text = ss.pop("suggested_prompt", None)
user_query   = st.chat_input("Ask anything…") or pending_text

if user_query and not ss.get("editing_idx"):
    # Auto-title conversation on first message
    if not messages:
        first_title = user_query[:28].strip() + ("…" if len(user_query) > 28 else "")
        db.update_session_title(ss["current_sid"], first_title)

    # ── User Bubble ──
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_query)

    # ── Streaming AI Response ──
    with st.chat_message("assistant", avatar="⚡"):
        ph = st.empty()
        accumulated = ""
        streamed_sources = []

        for pkt in chat_engine.stream_chat_response(
            user_message=user_query,
            temperature=ss["temperature"],
            top_p=ss["top_p"],
            top_k=ss["top_k"],
            max_new_tokens=ss["max_tokens"],
            use_rag=ss["use_rag"]
        ):
            accumulated = pkt.get("accumulated", accumulated)
            if pkt.get("sources"):
                streamed_sources = pkt["sources"]

            if not pkt.get("done"):
                ph.markdown(f'<div class="streaming-text">{accumulated}<span class="streaming-cursor"></span></div>', unsafe_allow_html=True)
                time.sleep(ss["stream_ms"] / 1000.0)
            else:
                ph.markdown(accumulated)

        # Render sources immediately under completed stream
        if streamed_sources:
            with st.expander(f"📑 Sources  ({len(streamed_sources)} reference{'s' if len(streamed_sources) > 1 else ''})", expanded=True):
                for s in streamed_sources:
                    fname     = s.get("filename",   "Document")
                    page      = s.get("page_range", str(s.get("page_number", "?")))
                    tot_pages = s.get("total_pages", "?")
                    score     = s.get("similarity_score", 0)
                    preview   = s.get("preview", "")[:200]
                    st.markdown(f"""
<div class="citation-card">
  <div class="citation-head">
    <span>📄 {fname}</span>
    <span class="badge-page">📖 Page {page} / {tot_pages}</span>
    <span class="badge-score">🎯 {score}% match</span>
  </div>
  <div class="citation-body">"{preview}..."</div>
</div>""", unsafe_allow_html=True)

    st.rerun()
