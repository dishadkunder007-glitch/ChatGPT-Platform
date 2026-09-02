"""
LocalGPT: Tokenizer Engine
Provides advanced tokenization, visual segmentation, vocabulary lookup, and token analytics.
"""

from typing import List, Dict, Any, Tuple, Optional
import colorsys
import html
import pandas as pd


class XRayTokenizer:
    """
    Wraps Hugging Face Tokenizers (or a built-in fallback) to provide rich token analysis,
    character offset mapping, visual chip rendering, and vocabulary inspection.
    """

    def __init__(self, model_name: str = "gpt2"):
        self.model_name = model_name
        self.hf_tokenizer = None
        self._load_tokenizer()

    def _load_tokenizer(self):
        """Attempts to load the Hugging Face tokenizer with a graceful fallback."""
        try:
            from transformers import AutoTokenizer
            try:
                self.hf_tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=True)
            except Exception:
                self.hf_tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.hf_tokenizer.pad_token is None:
                self.hf_tokenizer.pad_token = self.hf_tokenizer.eos_token
        except Exception as e:
            print(f"[XRayTokenizer] Note: Could not load '{self.model_name}' from HuggingFace ({e}). Using built-in fallback tokenizer.")
            self.hf_tokenizer = None

    def tokenize(self, text: str) -> Dict[str, Any]:
        """
        Tokenizes the input text and returns a comprehensive token breakdown dictionary.
        """
        if not text:
            text = " "

        if self.hf_tokenizer is not None:
            encoding = self.hf_tokenizer(
                text,
                return_offsets_mapping=True,
                add_special_tokens=False
            )
            token_ids = encoding["input_ids"]
            offsets = encoding.get("offset_mapping", [])

            # Convert IDs to tokens and human-friendly display strings
            raw_tokens = self.hf_tokenizer.convert_ids_to_tokens(token_ids)
            clean_tokens = [self.hf_tokenizer.decode([tid]) for tid in token_ids]
        else:
            # Fallback regex-based whitespace & punctuation tokenizer
            import re
            words = re.findall(r"\w+|[^\w\s]|\s+", text)
            token_ids = [abs(hash(w)) % 50257 for w in words]
            raw_tokens = [w.replace(" ", "Ġ") if w.startswith(" ") else w for w in words]
            clean_tokens = words
            offsets = []
            curr = 0
            for w in words:
                offsets.append((curr, curr + len(w)))
                curr += len(w)

        # Generate colors for visual distinction
        colors = self.generate_token_colors(len(token_ids))

        # Build token details
        token_details = []
        for i, (tid, raw_t, clean_t) in enumerate(zip(token_ids, raw_tokens, clean_tokens)):
            start, end = offsets[i] if i < len(offsets) else (0, 0)
            orig_slice = text[start:end] if start < len(text) and end <= len(text) else clean_t
            
            try:
                byte_repr = " ".join(f"0x{b:02X}" for b in clean_t.encode("utf-8"))
            except Exception:
                byte_repr = "N/A"

            token_details.append({
                "index": i,
                "token_id": tid,
                "display_token": clean_t,
                "raw_token": raw_t,
                "char_length": len(clean_t),
                "start_char": start,
                "end_char": end,
                "original_slice": repr(orig_slice),
                "byte_hex": byte_repr,
                "color": colors[i]
            })

        return {
            "text": text,
            "token_ids": token_ids,
            "clean_tokens": clean_tokens,
            "raw_tokens": raw_tokens,
            "offsets": offsets,
            "colors": colors,
            "token_details": token_details,
            "num_tokens": len(token_ids)
        }

    def generate_token_colors(self, count: int) -> List[str]:
        """Generates visually pleasing distinct pastel colors for token chips."""
        colors = []
        for i in range(count):
            hue = (i * 0.618033988749895) % 1.0  # Golden ratio color distribution
            # Saturation 0.65, Lightness 0.45 for dark-mode friendliness
            r, g, b = colorsys.hls_to_rgb(hue, 0.42, 0.70)
            colors.append(f"rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.45)")
        return colors

    def get_token_dataframe(self, text: str) -> pd.DataFrame:
        """Returns tokenization details structured as a pandas DataFrame."""
        tok_data = self.tokenize(text)
        df = pd.DataFrame(tok_data["token_details"])
        if not df.empty:
            df = df[["index", "token_id", "display_token", "raw_token", "char_length", "start_char", "end_char", "byte_hex"]]
            df.columns = ["Index", "Token ID", "Decoded String", "Raw Token", "Length", "Start Pos", "End Pos", "Hex Bytes"]
        return df

    def get_colored_html(self, text: str) -> str:
        """
        Renders the tokenized text into high-contrast HTML chips with hover tooltips.
        """
        tok_data = self.tokenize(text)
        chips = []
        for d in tok_data["token_details"]:
            escaped_display = html.escape(d["display_token"]).replace(" ", "&nbsp;").replace("\n", "&para;<br/>")
            escaped_raw = html.escape(str(d["raw_token"]))
            tid = d["token_id"]
            idx = d["index"]
            color = d["color"]

            chip_html = (
                f'<span class="xray-token-chip" '
                f'style="background-color: {color}; border: 1px solid rgba(255,255,255,0.2); '
                f'padding: 3px 6px; margin: 2px 3px; border-radius: 6px; display: inline-block; '
                f'font-family: monospace; font-size: 0.95rem; cursor: pointer; transition: transform 0.15s ease;" '
                f'title="Token #{idx} | ID: {tid} | Raw: {escaped_raw}">'
                f'{escaped_display}'
                f'<sub style="font-size: 0.65em; opacity: 0.8; margin-left: 3px;">#{idx}</sub>'
                f'</span>'
            )
            chips.append(chip_html)

        return '<div style="line-height: 2.2; padding: 12px; background: rgba(18, 22, 34, 0.6); border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);">' + "".join(chips) + '</div>'

    def get_vocab_stats(self) -> Dict[str, Any]:
        """Returns vocabulary metadata."""
        if self.hf_tokenizer is not None:
            return {
                "vocab_size": self.hf_tokenizer.vocab_size,
                "bos_token": str(self.hf_tokenizer.bos_token),
                "eos_token": str(self.hf_tokenizer.eos_token),
                "pad_token": str(self.hf_tokenizer.pad_token),
                "unk_token": str(self.hf_tokenizer.unk_token),
                "is_fast": self.hf_tokenizer.is_fast,
                "model_max_length": getattr(self.hf_tokenizer, "model_max_length", 1024)
            }
        return {
            "vocab_size": 50257,
            "bos_token": "<|endoftext|>",
            "eos_token": "<|endoftext|>",
            "pad_token": "<|endoftext|>",
            "unk_token": "<|unk|>",
            "is_fast": False,
            "model_max_length": 1024
        }

    def inspect_token(self, query: str) -> Dict[str, Any]:
        """Inspects a specific token string or ID."""
        if self.hf_tokenizer is None:
            return {"query": query, "found": False, "note": "HF tokenizer not loaded."}

        try:
            if query.isdigit():
                token_id = int(query)
                decoded = self.hf_tokenizer.decode([token_id])
                raw = self.hf_tokenizer.convert_ids_to_tokens(token_id)
            else:
                raw = query
                token_id = self.hf_tokenizer.convert_tokens_to_ids(query)
                decoded = self.hf_tokenizer.decode([token_id]) if token_id is not None else ""

            return {
                "query": query,
                "token_id": token_id,
                "raw_token": raw,
                "decoded": decoded,
                "byte_representation": [b for b in decoded.encode("utf-8")],
                "found": True
            }
        except Exception as e:
            return {"query": query, "found": False, "error": str(e)}

    def decode(self, token_ids: List[int]) -> str:
        """Decodes token IDs back into string."""
        if self.hf_tokenizer is not None:
            return self.hf_tokenizer.decode(token_ids)
        return "".join([f"[T_{tid}]" for tid in token_ids])
