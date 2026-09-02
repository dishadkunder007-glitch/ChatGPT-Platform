# LocalGPT: Privacy-First Local AI Assistant

LocalGPT is an open-source, fully local AI assistant that runs Large Language Models (LLMs) entirely on your local hardware without sending your prompts or documents to external servers.

## Key Capabilities

1. **Local Conversational AI**: Run open-weights models like Qwen 2.5, TinyLlama, GPT-2, and OPT with customizable system prompts, temperature, and top-p sampling.
2. **Retrieval-Augmented Generation (RAG)**: Ingest documents (PDF, Markdown, DOCX, TXT, CSV, Code) into a local vector database to answer queries with direct source citations.
3. **Mechanistic Interpretability (X-Ray)**: Inspect attention matrices across all layers and heads, explore Logit Lens early token predictions, observe Residual Stream L2 norm growth, and track representation drift.
4. **Persistent Memory & Sessions**: Save multi-turn conversation sessions to local SQLite databases with sliding window context management.
5. **Zero Data Leakage**: All computation (tokenization, neural forward passes, vector search, and generation) executes locally on your CPU or GPU.
