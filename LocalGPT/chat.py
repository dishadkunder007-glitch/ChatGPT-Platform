"""
LocalGPT: Conversational Chat Engine & Multi-Turn Context Builder
Orchestrates multi-turn local chat, token streaming generation, system prompt enforcement,
hyperparameter tuning, and seamless RAG context integration.

Implements the standard conversation lifecycle:
Conversation -> Message History -> Context Builder -> LLM -> Response -> Save Response.
"""

from typing import List, Dict, Any, Generator, Optional, Tuple, Union
import time

try:
    from .model import XRayModel
    from .memory import MemoryManager, ChatMessage
    from .rag import RAGPipeline
    from .semantic_responder import generate_dynamic_response
except (ImportError, ValueError):
    from model import XRayModel
    from memory import MemoryManager, ChatMessage
    from rag import RAGPipeline
    from semantic_responder import generate_dynamic_response


class ContextBuilder:
    """
    Builds the multi-turn context payload from message history for LLM generation.
    Supports chat templates (ChatML, LLaMA, Qwen) and plain-text role formatting.
    """

    def __init__(self, tokenizer=None, max_context_tokens: int = 2048):
        self.tokenizer = tokenizer
        self.max_context_tokens = max_context_tokens

    def build_context(
        self,
        history: List[ChatMessage],
        current_query: str,
        system_prompt: str = "You are LocalGPT, a helpful, clear, and concise AI assistant.",
        rag_context_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Assembles all prior conversation turns and current input into structured messages.
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Append previous message history turns
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Append the new user prompt (or augmented RAG prompt)
        final_user_content = rag_context_prompt if rag_context_prompt else current_query
        messages.append({"role": "user", "content": final_user_content})

        return messages

    def build_flat_context_string(
        self,
        history: List[ChatMessage],
        current_query: str,
        system_prompt: str = "You are LocalGPT, a helpful, clear, and concise AI assistant.",
        rag_context_prompt: Optional[str] = None
    ) -> str:
        """
        Constructs a human-readable multi-turn plain text transcript:
        System: ...
        User: What is Machine Learning?
        AI: Machine Learning is...
        User: What are its types?
        AI: The main types are...
        User: Give me an example.
        AI:
        """
        lines = [f"System: {system_prompt}"]

        for msg in history:
            role_label = "User" if msg.role == "user" else "AI"
            lines.append(f"{role_label}: {msg.content}")

        final_user_content = rag_context_prompt if rag_context_prompt else current_query
        lines.append(f"User: {final_user_content}")
        lines.append("AI:")

        return "\n\n".join(lines)


class ChatEngine:
    """
    Manages the conversational lifecycle for LocalGPT.
    Pipeline:
    Conversation -> Message History -> Context Builder -> LLM -> Response -> Save Response.
    """

    def __init__(
        self,
        model: Optional[XRayModel] = None,
        memory: Optional[MemoryManager] = None,
        rag_pipeline: Optional[RAGPipeline] = None
    ):
        self.model = model or XRayModel()
        self.memory = memory or MemoryManager()
        self.rag = rag_pipeline or RAGPipeline()
        self.context_builder = ContextBuilder(tokenizer=self.model.tokenizer)

    def set_system_prompt(self, prompt: str):
        self.memory.set_system_prompt(prompt)

    def generate_chat_response(
        self,
        user_message: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        max_new_tokens: int = 128,
        use_rag: bool = False,
        rag_top_k: int = 4
    ) -> Dict[str, Any]:
        """
        Executes the multi-turn conversational loop:
        1. Conversation input received
        2. Retrieve Message History from memory
        3. Context Builder merges system prompt + past turns + new query (+ optional RAG)
        4. LLM forward generation
        5. Extract Response
        6. Save User & Assistant Responses into Memory & SQLite Database
        """
        sources = []
        rag_prompt = None

        # Step 1: Optional RAG Retrieval
        if use_rag:
            chunks = self.rag.retrieve_context(user_message, top_k=rag_top_k)
            if chunks:
                rag_prompt = self.rag.build_rag_prompt(user_message, chunks)
                sources = self.rag.get_sources_summary(chunks)

        # Step 2: Retrieve current Message History (before adding new turn)
        history = self.memory.get_history()

        # Step 3: Context Builder builds full multi-turn context
        structured_context = self.context_builder.build_context(
            history=history,
            current_query=user_message,
            system_prompt=self.memory.system_prompt,
            rag_context_prompt=rag_prompt
        )

        # Step 4: LLM Generation conditioned on the entire conversation history
        start_time = time.time()
        response_text = self.model.generate_response(
            prompt=structured_context,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k
        )
        duration = time.time() - start_time

        # Step 5 & 6: Save User Message and Assistant Response in Memory & Database
        user_tokens = len(self.model.tokenizer.tokenize(user_message)["token_ids"])
        asst_tokens = len(self.model.tokenizer.tokenize(response_text)["token_ids"])

        self.memory.add_user_message(user_message, token_count=user_tokens, metadata={"rag_used": use_rag})
        self.memory.add_assistant_message(
            response_text,
            token_count=asst_tokens,
            metadata={"generation_time_sec": round(duration, 3), "sources": sources}
        )

        return {
            "response": response_text,
            "sources": sources,
            "tokens_generated": asst_tokens,
            "generation_time_sec": round(duration, 3),
            "tokens_per_sec": round(asst_tokens / max(duration, 0.001), 1),
            "turn_count": len(self.memory.get_history()) // 2
        }

    def stream_chat_response(
        self,
        user_message: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        max_new_tokens: int = 128,
        use_rag: bool = False,
        rag_top_k: int = 4
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Yields tokens incrementally while maintaining multi-turn context.
        """
        sources = []
        rag_prompt = None

        if use_rag:
            chunks = self.rag.retrieve_context(user_message, top_k=rag_top_k)
            if chunks:
                rag_prompt = self.rag.build_rag_prompt(user_message, chunks)
                sources = self.rag.get_sources_summary(chunks)

        history = self.memory.get_history()

        # Build full multi-turn context
        structured_context = self.context_builder.build_context(
            history=history,
            current_query=user_message,
            system_prompt=self.memory.system_prompt,
            rag_context_prompt=rag_prompt
        )
        flat_context = self.context_builder.build_flat_context_string(
            history=history,
            current_query=user_message,
            system_prompt=self.memory.system_prompt,
            rag_context_prompt=rag_prompt
        )

        # Save user message
        user_tokens = len(self.model.tokenizer.tokenize(user_message)["token_ids"])
        self.memory.add_user_message(user_message, token_count=user_tokens, metadata={"rag_used": use_rag})

        # Synthetic fallback streaming simulation
        if self.model.is_synthetic:
            text = generate_dynamic_response(structured_context, rag_sources=sources)
            words = text.split(" ")
            accumulated = ""
            for i, w in enumerate(words):
                token_piece = w + (" " if i < len(words) - 1 else "")
                accumulated += token_piece
                time.sleep(0.015)
                yield {
                    "delta": token_piece,
                    "accumulated": accumulated,
                    "done": False,
                    "sources": sources
                }

            asst_tokens = len(words)
            self.memory.add_assistant_message(accumulated.strip(), token_count=asst_tokens, metadata={"sources": sources})
            yield {"delta": "", "accumulated": accumulated.strip(), "done": True, "sources": sources}
            return

        # Real model token generation
        try:
            # Apply chat template if available for instruction-tuned models like Qwen
            hf_tok = getattr(self.model.tokenizer, "hf_tokenizer", None)
            if hf_tok is not None and getattr(hf_tok, "chat_template", None):
                try:
                    formatted_input = hf_tok.apply_chat_template(
                        structured_context, tokenize=False, add_generation_prompt=True
                    )
                except Exception:
                    formatted_input = flat_context
            else:
                formatted_input = flat_context

            tok_data = self.model.tokenizer.tokenize(formatted_input)
            current_ids = list(tok_data["token_ids"])
            accumulated = ""

            import torch
            import torch.nn.functional as F
            import numpy as np

            for step in range(max_new_tokens):
                input_tensor = torch.tensor([current_ids], dtype=torch.long, device=self.model.device)
                with torch.no_grad():
                    outputs = self.model.model(input_tensor, output_attentions=False, output_hidden_states=False)
                    logits = outputs.logits[0, -1].detach().cpu()
                    
                    if temperature > 0:
                        scaled_logits = logits / max(temperature, 0.05)
                        probs = F.softmax(scaled_logits, dim=-1).numpy()
                        # Apply top-k filtering
                        if top_k and top_k > 0:
                            top_k_indices = np.argsort(probs)[::-1][:top_k]
                            top_k_probs = probs[top_k_indices]
                            top_k_probs = top_k_probs / np.sum(top_k_probs)
                            selected_id = int(np.random.choice(top_k_indices, p=top_k_probs))
                        else:
                            selected_id = int(np.random.choice(len(probs), p=probs))
                    else:
                        probs = F.softmax(logits, dim=-1).numpy()
                        selected_id = int(np.argmax(probs))

                eos_id = getattr(hf_tok, "eos_token_id", None)
                if eos_id is not None and selected_id == eos_id:
                    break

                current_ids.append(selected_id)
                new_token = self.model.tokenizer.decode([selected_id])
                accumulated += new_token

                # Stop if turn boundary is generated
                if any(m in accumulated for m in ["\nUser:", "\nHuman:", "\nAI:", "\nAssistant:", "<|im_end|>", "<|endoftext|>"]):
                    for m in ["\nUser:", "\nHuman:", "\nAI:", "\nAssistant:", "<|im_end|>", "<|endoftext|>"]:
                        if m in accumulated:
                            accumulated = accumulated.split(m)[0]
                    break

                yield {
                    "delta": new_token,
                    "accumulated": accumulated,
                    "done": False,
                    "sources": sources
                }

            asst_tokens = len(current_ids) - len(tok_data["token_ids"])
            self.memory.add_assistant_message(accumulated.strip(), token_count=asst_tokens, metadata={"sources": sources})
            yield {"delta": "", "accumulated": accumulated.strip(), "done": True, "sources": sources}

        except Exception:
            resp = self.model.generate_response(structured_context, max_new_tokens, temperature, top_p, top_k)
            asst_tokens = len(self.model.tokenizer.tokenize(resp)["token_ids"])
            self.memory.add_assistant_message(resp, token_count=asst_tokens, metadata={"sources": sources})
            yield {"delta": resp, "accumulated": resp, "done": True, "sources": sources}

    # ── Regenerate ────────────────────────────────────────────────────────────

    def regenerate_last_response(
        self,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        max_new_tokens: int = 180,
        use_rag: bool = False,
        rag_top_k: int = 4
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Removes the last assistant reply from memory, then re-generates a fresh
        response for the same user message using the current generation settings.
        Yields streaming packets identical to stream_chat_response.
        """
        history = self.memory.get_history()
        if not history:
            yield {"delta": "", "accumulated": "", "done": True, "sources": []}
            return

        # Find the last user message (strip any trailing assistant turn)
        last_user_content = None
        for msg in reversed(history):
            if msg.role == "user":
                last_user_content = msg.content
                break

        if not last_user_content:
            yield {"delta": "", "accumulated": "", "done": True, "sources": []}
            return

        # Remove the last assistant message from DB and memory
        self.memory.pop_last_assistant()

        # Re-run generation (will re-add messages)
        yield from self.stream_chat_response(
            user_message=last_user_content,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_new_tokens=max_new_tokens,
            use_rag=use_rag,
            rag_top_k=rag_top_k
        )

    # ── Edit user message ─────────────────────────────────────────────────────

    def edit_and_resubmit(
        self,
        new_user_content: str,
        edit_turn_index: int,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        max_new_tokens: int = 180,
        use_rag: bool = False
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Edits a past user message and removes all subsequent messages,
        then re-generates from that point forward.
        edit_turn_index is the index in get_history() of the user message to edit.
        """
        history = self.memory.get_history()
        if edit_turn_index >= len(history):
            yield {"delta": "", "accumulated": "", "done": True, "sources": []}
            return

        # Truncate memory to just before this turn
        self.memory.truncate_after(edit_turn_index)

        # Re-generate with the new user content
        yield from self.stream_chat_response(
            user_message=new_user_content,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_new_tokens=max_new_tokens,
            use_rag=use_rag
        )

