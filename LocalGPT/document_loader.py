"""
LocalGPT: Multi-Format Document Parser & Semantic Chunker — Enhanced
Extracts text from PDF (page-by-page), DOCX, TXT, MD, CSV, JSON, and code files.
All chunks carry rich metadata: filename, page_number, page_range, char_offset, word_count.
"""

import os
import re
import csv
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class DocumentChunk:
    chunk_id:    str
    doc_id:      str
    text:        str
    chunk_index: int
    metadata:    Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentLoader:
    """
    Loads various document types into clean plain text with per-page metadata
    so that source references can show exact page numbers.
    """

    SUPPORTED_EXTENSIONS = [
        ".txt", ".md", ".markdown", ".pdf", ".docx",
        ".csv", ".json", ".py", ".js", ".html", ".css",
        ".java", ".cpp", ".c"
    ]

    def load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Loads a single document file and returns:
          - doc_id, filename, file_type, file_size
          - text: full clean text
          - pages: list of {page_num, text, char_start, char_end}
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        filename  = os.path.basename(file_path)
        ext       = os.path.splitext(filename)[1].lower()
        file_size = os.path.getsize(file_path)
        doc_id    = hashlib.sha256(f"{filename}_{file_size}".encode()).hexdigest()[:16]

        pages_info: List[Dict[str, Any]] = []
        text = ""

        if ext in [".txt", ".md", ".markdown", ".py", ".js", ".html", ".css", ".java", ".cpp", ".c"]:
            text = self._load_text_file(file_path)
            pages_info = [{"page_num": 1, "text": text, "char_start": 0, "char_end": len(text)}]
        elif ext == ".pdf":
            text, pages_info = self._load_pdf_file(file_path)
        elif ext == ".docx":
            text, pages_info = self._load_docx_file(file_path)
        elif ext == ".csv":
            text = self._load_csv_file(file_path)
            pages_info = [{"page_num": 1, "text": text, "char_start": 0, "char_end": len(text)}]
        elif ext == ".json":
            text = self._load_json_file(file_path)
            pages_info = [{"page_num": 1, "text": text, "char_start": 0, "char_end": len(text)}]
        else:
            text = self._load_text_file(file_path)
            pages_info = [{"page_num": 1, "text": text, "char_start": 0, "char_end": len(text)}]

        clean_text = self._clean_text(text)
        # Rebuild char offsets after clean
        for i, p in enumerate(pages_info):
            p["char_length"] = len(p.get("text", ""))

        return {
            "doc_id":    doc_id,
            "filename":  filename,
            "file_type": ext.lstrip("."),
            "file_path": file_path,
            "file_size": file_size,
            "text":      clean_text,
            "pages":     pages_info,
            "page_count": len(pages_info),
        }

    # ── Loaders ──────────────────────────────────────────────────────────────

    def _load_text_file(self, file_path: str) -> str:
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(file_path, "r", errors="ignore") as f:
            return f.read()

    def _load_pdf_file(self, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Extracts text page-by-page from PDF using pypdf."""
        text_parts: List[str] = []
        pages:      List[Dict[str, Any]] = []
        char_cursor = 0

        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_text = self._clean_text(page_text)
                if page_text.strip():
                    pages.append({
                        "page_num":   i + 1,
                        "text":       page_text,
                        "char_start": char_cursor,
                        "char_end":   char_cursor + len(page_text),
                    })
                    text_parts.append(page_text)
                    char_cursor += len(page_text) + 2  # +2 for "\n\n"
            return "\n\n".join(text_parts), pages

        except Exception as e:
            print(f"[DocumentLoader] PDF extraction warning ({e}), using text fallback.")
            raw = self._load_text_file(file_path)
            clean = re.sub(r"[^\x20-\x7E\n]", " ", raw)
            pages = [{"page_num": 1, "text": clean, "char_start": 0, "char_end": len(clean)}]
            return clean, pages

    def _load_docx_file(self, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extracts text from DOCX.
        Uses python-docx paragraph grouping to approximate page sections.
        """
        try:
            import docx
            doc = docx.Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            # Group every ~30 paragraphs as a synthetic "page"
            page_size = 30
            pages: List[Dict[str, Any]] = []
            char_cursor = 0
            for page_num, start_idx in enumerate(range(0, max(len(paragraphs), 1), page_size), start=1):
                page_paras = paragraphs[start_idx: start_idx + page_size]
                page_text = "\n\n".join(page_paras)
                pages.append({
                    "page_num":   page_num,
                    "text":       page_text,
                    "char_start": char_cursor,
                    "char_end":   char_cursor + len(page_text),
                })
                char_cursor += len(page_text) + 2

            full_text = "\n\n".join(paragraphs)
            return full_text, pages

        except Exception as e:
            print(f"[DocumentLoader] DOCX extraction warning ({e}).")
            text = self._load_text_file(file_path)
            return text, [{"page_num": 1, "text": text, "char_start": 0, "char_end": len(text)}]

    def _load_csv_file(self, file_path: str) -> str:
        lines = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers:
                for row_idx, row in enumerate(reader):
                    row_str = " | ".join(f"{h}: {v}" for h, v in zip(headers, row) if v.strip())
                    lines.append(f"Row {row_idx + 1}: {row_str}")
        return "\n".join(lines)

    def _load_json_file(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        return json.dumps(data, indent=2)

    def _clean_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class RecursiveCharacterChunker:
    """
    Splits document text into overlapping chunks with per-chunk page attribution.
    Each chunk carries: filename, page_number, page_range, chunk_index, char_length, word_count.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size    = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators    = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]

    def chunk_document(self, doc_data: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Splits loaded document into chunks, resolving page numbers from char offsets.
        """
        text = doc_data.get("text", "")
        if not text:
            return []

        doc_id    = doc_data.get("doc_id",    "unknown_doc")
        filename  = doc_data.get("filename",  "unknown_file")
        file_type = doc_data.get("file_type", "txt")
        pages     = doc_data.get("pages",     [])
        total_pages = doc_data.get("page_count", 1)

        raw_chunks = self._split_text(text, self.separators)

        # Build character position map to resolve page numbers
        char_cursor = 0
        chunks: List[DocumentChunk] = []

        for i, chunk_txt in enumerate(raw_chunks):
            chunk_txt = chunk_txt.strip()
            if not chunk_txt:
                continue

            chunk_start = char_cursor
            chunk_end   = char_cursor + len(chunk_txt)
            char_cursor = max(chunk_end - self.chunk_overlap, chunk_end)

            # Find which page(s) this chunk spans
            page_nums = self._resolve_pages(chunk_start, chunk_end, pages)
            page_label = (
                str(page_nums[0]) if len(page_nums) == 1
                else f"{page_nums[0]}–{page_nums[-1]}"
            ) if page_nums else "1"

            chunk_id = f"{doc_id}_chk_{i:04d}"
            meta = {
                "filename":     filename,
                "file_type":    file_type,
                "doc_id":       doc_id,
                "chunk_index":  i,
                "total_chunks": len(raw_chunks),
                "page_number":  page_nums[0] if page_nums else 1,
                "page_range":   page_label,
                "total_pages":  total_pages,
                "char_start":   chunk_start,
                "char_end":     chunk_end,
                "char_length":  len(chunk_txt),
                "word_count":   len(chunk_txt.split()),
            }

            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=chunk_txt,
                chunk_index=i,
                metadata=meta
            ))

        return chunks

    def _resolve_pages(
        self,
        char_start: int,
        char_end:   int,
        pages:      List[Dict[str, Any]]
    ) -> List[int]:
        """Returns sorted list of page numbers that overlap [char_start, char_end]."""
        if not pages:
            return [1]
        matched = []
        for p in pages:
            ps = p.get("char_start", 0)
            pe = p.get("char_end",   ps + p.get("char_length", 0))
            if ps <= char_end and pe >= char_start:
                matched.append(p["page_num"])
        return sorted(matched) if matched else [pages[0]["page_num"]]

    # ── Text splitting internals ──────────────────────────────────────────────

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        final_chunks = []
        separator    = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if re.search(re.escape(sep), text):
                separator      = sep
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)
        good_splits: List[str] = []

        for s in splits:
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    final_chunks.extend(self._merge_splits(good_splits, separator))
                    good_splits = []
                if not new_separators:
                    final_chunks.append(s[:self.chunk_size])
                else:
                    final_chunks.extend(self._split_text(s, new_separators))

        if good_splits:
            final_chunks.extend(self._merge_splits(good_splits, separator))

        return final_chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        docs: List[str] = []
        current_doc: List[str] = []
        total = 0

        for d in splits:
            _len = len(d)
            sep_len = len(separator) if total > 0 else 0
            if total + _len + sep_len > self.chunk_size:
                if current_doc:
                    doc = separator.join(current_doc)
                    if doc.strip():
                        docs.append(doc)
                    while total > self.chunk_overlap and current_doc:
                        total -= len(current_doc[0]) + (len(separator) if len(current_doc) > 1 else 0)
                        current_doc = current_doc[1:]
                current_doc.append(d)
                total += _len + (len(separator) if len(current_doc) > 1 else 0)
            else:
                current_doc.append(d)
                total += _len + sep_len

        if current_doc:
            doc = separator.join(current_doc)
            if doc.strip():
                docs.append(doc)

        return docs
