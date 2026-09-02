# 🔬 LLM-XRay: Interactive LLM Interpretability Platform

**LLM-XRay** is an interactive, visual mechanistic interpretability platform for dissecting and inspecting the internal workings of Transformer-based Large Language Models (GPT-2, DistilGPT-2, OPT, TinyLlama, etc.).

---

## 📁 Project Structure

```
LLM-XRay/
├── app.py                # Modern Streamlit UI with interactive tabs, custom CSS & presets
├── model.py              # Mechanistic PyTorch hooks for attention, hidden states, logit lens & MLP activations
├── tokenizer.py          # Token decomposition, vocabulary lookup, offset mapping & visual chips
├── visualization.py      # Interactive Plotly heatmaps, logit lens progression, and residual stream plots
└── requirements.txt      # Python dependencies (Streamlit, PyTorch, Transformers, Plotly, etc.)
```

---

## 🌟 Key Features

1. **🏷️ Token & Vocabulary Inspector**:
   - Subword tokenization, token IDs, byte/hex representation, whitespace visibility.
   - Interactive vocabulary search and token lookup.

2. **🧠 Attention X-Ray**:
   - Layer-by-layer, head-by-head interactive attention heatmaps with query-key tooltips.
   - Multi-head grid view for full layer comparison.
   - Attention Rollout (Abnar & Zuidema, 2020) displaying global information flow across layers.

3. **🔭 Logit Lens (Thought Progression)**:
   - Early un-embedding projection showing what the model "thinks" at intermediate layers.
   - 2D matrix (Layers $\times$ Token Positions) showing confidence and prediction emergence.

4. **📈 Residual Stream Dynamics**:
   - Layer-wise L2 norm growth curves.
   - Cosine similarity drift tracking representation stability across depth.

5. **⚡ Neuron Activation Explorer**:
   - MLP activation sparsity and top firing neuron identification per layer.

6. **✍️ Live Step-by-Step Generation Tracer**:
   - Autoregressive token generation with real-time confidence and entropy tracking.

7. **🧪 Built-in Interpretability Presets**:
   - Factual Recall (*"The Eiffel Tower is located in the city of"*)
   - Induction Head Test (*"Mr. Dursley lived at number 4 Privet Drive. Mr. Dursley"*)
   - Indirect Object Identification (*"When Mary and John went to the store, John gave a drink to"*)
   - Arithmetic reasoning & Sentiment shift.

---

## 🚀 Quick Start & How to Run

### 1. Install Dependencies
```bash
pip install -r LLM-XRay/requirements.txt
```

### 2. Launch the Application
```bash
streamlit run LLM-XRay/app.py
```

### 3. Open in Browser
Streamlit will automatically launch the web interface at `http://localhost:8501`.
