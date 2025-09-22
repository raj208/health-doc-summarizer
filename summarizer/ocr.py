# summarizer/ocr.py
import os
from typing import Dict, Any
from PIL import Image
from .utils import is_pdf, is_image, pdf_to_images, image_from_file, extract_pdf_metadata
from .postprocess import language_aware_normalize
import numpy as np


_OCR_ERR = None
_PPSTRUCTURE_ERR = None

# Base OCR (required)
try:
    from paddleocr import PaddleOCR
except Exception as e:
    _OCR_ERR = e
    PaddleOCR = None

# Table extraction (optional): prefer PPStructure; fall back to TableSystem
PPStructure = None
TableSystem = None
try:
    # Newer & recommended API
    from paddleocr import PPStructure as _PPStructure
    PPStructure = _PPStructure
except Exception as e1:
    try:
        # Older API
        from paddleocr.ppstructure.table.predict_table import TableSystem as _TableSystem
        TableSystem = _TableSystem
    except Exception as e2:
        _PPSTRUCTURE_ERR = (e1, e2)

def get_ocr_engine(lang_mode: str = "multi"):
    if PaddleOCR is None:
        raise RuntimeError(f"PaddleOCR not available: {_OCR_ERR}")
    # 'en' for English only; 'ch' is multilingual model that also handles Latin scripts
    recog_lang = "en" if lang_mode == "en" else "ch"
    return PaddleOCR(lang=recog_lang, use_angle_cls=True, show_log=False)

def ocr_file(path: str, lang_mode: str = "multi", doc_type: str = "default") -> Dict[str, Any]:
    """
    Returns:
    {
      'metadata': {...},
      'pages': [ {'text': '...', 'tables': [html,...], 'page': N}, ... ]
    }
    """
    ocr = get_ocr_engine(lang_mode)
    pages = []
    meta = {}

    if is_pdf(path):
        images = pdf_to_images(path, dpi=300)
        meta = extract_pdf_metadata(path)
        for idx, img in enumerate(images, 1):
            p = _ocr_image(img, ocr, need_tables=(doc_type == "labs"), lang_mode=lang_mode)
            p["page"] = idx
            pages.append(p)
    elif is_image(path):
        img = image_from_file(path)
        p = _ocr_image(img, ocr, need_tables=(doc_type == "labs"), lang_mode=lang_mode)
        p["page"] = 1
        pages.append(p)
    else:
        raise ValueError("Unsupported file type")
    return {"metadata": meta, "pages": pages}

def _ocr_image(img: Image.Image, ocr, need_tables: bool, lang_mode: str) -> Dict[str, Any]:
    # ----- Text OCR -----
    # result = ocr.ocr(img, cls=True)
    img_np = np.array(img.convert("RGB"))   # HxWx3 uint8
    result = ocr.ocr(img_np, cls=True)

    lines = []
    # result: list per image; each item is list of [box, (text, conf)]
    for r in result:
        for b in r:
            txt, conf = b[1]
            if txt:
                lines.append(txt)
    text = language_aware_normalize("\n".join(lines), lang_mode)

    # ----- Table extraction (optional) -----
    tables = []
    if need_tables:
        try:
            if PPStructure is not None:
                # PPStructure API (preferred)
                # Disable layout; we only need tables for Labs
                table_engine = PPStructure(layout=False, table=True, show_log=False)
                res = table_engine(img_np )  # returns list of dicts per region
                # Extract HTML from table regions
                for item in res:
                    if item.get("type") == "table":
                        html = item.get("res", {}).get("html")
                        if html:
                            tables.append(html)
            elif TableSystem is not None:
                # Older API: no kwargs in constructor
                table_engine = TableSystem()
                res = table_engine(img_np)
                for t in res:
                    html = t.get("res", {}).get("html", "")
                    if html:
                        tables.append(html
                                      
                                      )
            # else: no table module available -> silently skip
        except TypeError:
            # Handle signature mismatches gracefully (e.g., unexpected kwargs)
            try:
                # Retry with a no-arg instantiation if we failed above
                if TableSystem is not None:
                    table_engine = TableSystem()
                    res = table_engine(img_np)
                    for t in res:
                        html = t.get("res", {}).get("html", "")
                        if html:
                            tables.append(html)
            except Exception:
                pass
        except Exception:
            # Any table error shouldn't block OCR; just skip tables
            pass

    return {"text": text, "tables": tables}
