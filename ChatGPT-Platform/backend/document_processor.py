import os
import json
import io
import csv
from typing import List, Dict, Any

try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine = RapidOCR()
    OCR_AVAILABLE = True
except Exception:
    _ocr_engine = None
    OCR_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def extract_text_from_file(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Extracts text and chunks from PDF, DOCX, TXT, CSV, JSON, MD, and image files.
    Supports OCR for scanned PDF pages and images.
    Returns list of dicts: [{"text": str, "page": int/None, "chunk_id": int, "filename": str}]
    """
    ext = os.path.splitext(filename)[1].lower()
    raw_chunks = []

    if ext == ".pdf":
        if PYPDF_AVAILABLE:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                # If page text is missing or extremely sparse, check for embedded images and run OCR
                if len(text.strip()) < 20 and OCR_AVAILABLE:
                    try:
                        images = getattr(page, "images", [])
                        if len(images) > 0:
                            img_texts = []
                            for img in images:
                                try:
                                    res, _ = _ocr_engine(img.data)
                                    if res:
                                        img_texts.append(" ".join([line[1] for line in res]))
                                except Exception:
                                    pass
                            if img_texts:
                                ocr_combined = "\n".join(img_texts)
                                text = f"{text}\n{ocr_combined}".strip() if text.strip() else ocr_combined
                    except Exception:
                        pass

                if text.strip():
                    raw_chunks.append({"text": text.strip(), "page": page_idx + 1})
        else:
            raw_chunks.append({"text": file_bytes.decode("utf-8", errors="ignore"), "page": 1})

    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        if OCR_AVAILABLE:
            try:
                res, _ = _ocr_engine(file_bytes)
                if res:
                    ocr_text = " ".join([line[1] for line in res])
                    if ocr_text.strip():
                        raw_chunks.append({"text": ocr_text.strip(), "page": 1})
            except Exception:
                pass

    elif ext in [".docx", ".doc"]:
        if DOCX_AVAILABLE:
            doc = docx.Document(io.BytesIO(file_bytes))
            full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            raw_chunks.append({"text": full_text, "page": 1})
        else:
            raw_chunks.append({"text": file_bytes.decode("utf-8", errors="ignore"), "page": 1})

    elif ext == ".csv":
        try:
            content = file_bytes.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(content))
            rows = [", ".join(row) for row in reader if row]
            raw_chunks.append({"text": "\n".join(rows), "page": 1})
        except Exception:
            raw_chunks.append({"text": file_bytes.decode("utf-8", errors="ignore"), "page": 1})

    elif ext == ".json":
        try:
            data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
            formatted = json.dumps(data, indent=2)
            raw_chunks.append({"text": formatted, "page": 1})
        except Exception:
            raw_chunks.append({"text": file_bytes.decode("utf-8", errors="ignore"), "page": 1})

    else: # txt, md, etc.
        raw_chunks.append({"text": file_bytes.decode("utf-8", errors="ignore"), "page": 1})

    # Sub-chunk if texts are long (> 600 characters)
    final_chunks = []
    chunk_counter = 0

    for item in raw_chunks:
        text = item["text"]
        page = item.get("page", 1)
        
        # Split into ~500 character chunks with 50 char overlap
        chunk_size = 500
        overlap = 50
        
        if len(text) <= chunk_size:
            final_chunks.append({
                "chunk_id": chunk_counter,
                "text": text,
                "page": page,
                "filename": filename
            })
            chunk_counter += 1
        else:
            start = 0
            while start < len(text):
                chunk = text[start:start + chunk_size]
                final_chunks.append({
                    "chunk_id": chunk_counter,
                    "text": chunk.strip(),
                    "page": page,
                    "filename": filename
                })
                chunk_counter += 1
                start += (chunk_size - overlap)

    return final_chunks
