import os, uuid, io, re, json, math
from typing import List, Dict, Any, Tuple
from PIL import Image
from pdf2image import convert_from_path
from pypdf import PdfReader

IMG_EXTS = {'.png','.jpg','.jpeg','.tiff','.bmp','.webp'}
PDF_EXTS = {'.pdf'}

def is_pdf(path: str) -> bool:
    return os.path.splitext(path.lower())[1] in PDF_EXTS

def is_image(path: str) -> bool:
    return os.path.splitext(path.lower())[1] in IMG_EXTS

def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[Image.Image]:
    pages = convert_from_path(pdf_path, dpi=dpi, fmt='png')
    return pages

def image_from_file(path: str) -> Image.Image:
    return Image.open(path).convert('RGB')

def approx_token_len(text: str) -> int:
    # very rough fallback tokenizer (~4 chars/token)
    return max(1, math.ceil(len(text) / 4))

def chunk_text(text: str, max_tokens: int = 800) -> List[str]:
    # simple greedy chunker by characters approximated to tokens
    target_chars = max_tokens * 4
    parts = []
    start = 0
    while start < len(text):
        end = min(len(text), start + target_chars)
        # try to cut at newline
        cut = text.rfind('\n\n', start, end)
        if cut == -1:
            cut = text.rfind('\n', start, end)
        if cut == -1 or cut <= start + target_chars * 0.5:
            cut = end
        parts.append(text[start:cut].strip())
        start = cut
    return [p for p in parts if p.strip()]

def extract_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    try:
        reader = PdfReader(pdf_path)
        meta = reader.metadata or {}
        return {
            'pages': len(reader.pages),
            'title': str(meta.get('/Title', '')),
            'author': str(meta.get('/Author', '')),
            'producer': str(meta.get('/Producer', '')),
        }
    except Exception:
        return {'pages': None}
