# Transformer Architecture and Attention Mechanisms

The Transformer architecture, introduced in "Attention Is All You Need" (Vaswani et al., 2017), relies on the Self-Attention mechanism to model dependencies between tokens regardless of their distance in the sequence.

## Mathematical Formulation

1. **Scaled Dot-Product Attention**:
   $$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k}}\right) V$$
   Where $Q$ (Query), $K$ (Key), and $V$ (Value) are linear projections of input representations, and $d_k$ is the dimensionality of the key vectors.

2. **Multi-Head Attention (MHA)**:
   $$\text{MHA}(Q, K, V) = \text{Concat}(\text{head}_1, \dots, \text{head}_h) W^O$$
   Each head projects inputs into a different representation subspace, allowing the model to simultaneously attend to information from different representation subspaces at different positions.

3. **Residual Stream Dynamics**:
   In modern decoder-only transformers (GPT, LLaMA, Qwen), representations pass through a shared residual stream where each layer adds its computed update:
   $$x_{l+1} = x_l + \text{MHA}(\text{LN}(x_l)) + \text{MLP}(\text{LN}(x'_l))$$
   The L2 vector norm typically grows monotonically as layer depth increases, while cosine similarity between adjacent layers reveals representation stability and semantic convergence.
