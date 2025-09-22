<!-- # health-doc-summarizer -->
<!-- OCR + LLM-based clinical summarizer built with Django, PaddleOCR, and Hugging Face/OpenAI. -->
# medvault

A Django-based application for extracting and summarizing clinical documents.  
It uses **PaddleOCR** for OCR (English + multilingual, with table extraction for labs) and integrates with **OpenAI** or **Hugging Face (Qwen)** for structured summarization.

---
## Architecture Overview
┌──────────┐        1 HTTP POST /upload          ┌─────────────────────┐
│  Client  │ ───────────────────────────────────▶ │ Django View (upload)│
│ (Web UI) │ ◀────────── 2 HTML (detail link) ───└──────────┬──────────┘
└──────────┘                                               3 │
                                                            │ create Document(status=uploaded)
                                                            │ save file → MEDIA/uploads/...
                                                            │ compute file_hash (sha256)
                                                            │ check cache by file_hash
                                                            ▼
                                              ┌─────────────────────────┐
                                              │   Object Store (local)  │
                                              │   original file saved   │
                                              └───────────┬─────────────┘
                                                          │
                                             4 load/convert image(s) / rasterize PDF
                                                          │
                                                          ▼
                                     ┌───────────────────────────────┐
                                     │  Preprocess (variants)        │
                                     │  upscale, CLAHE, threshold    │
                                     └──────────────┬────────────────┘
                                                    │ for each variant
                                                    ▼
                                       ┌─────────────────────────┐
                                       │ PaddleOCR (det+cls+rec)│
                                       │ + PP-Structure (Labs)  │
                                       └──────────┬─────────────┘
                                                  │ 5 text lines (+ optional table HTML)
                                                  ▼
                                      ┌───────────────────────────┐
                                      │ Post-process & Redact PHI │
                                      │ NFKC, ftfy, zero-width    │
                                      └──────────┬────────────────┘
                                                 │ 6 cleaned_text
                                                 ▼
                                  ┌───────────────────────────┐
                                  │ Chunker (IDs + overlaps)  │
                                  │ token-aware splits         │
                                  └──────────┬────────────────┘
                                             │ 7 chunks[]
                                             ▼
                           ┌─────────────────────────────────────┐
                           │ Summarizer (LLM)                    │
                           │  a) OpenAI Chat w/ JSON format      │
                           │  b) HF Qwen via Inference API       │
                           └──────────┬──────────────────────────┘
                                      │ 8 raw_model_text
                                      ▼
                            ┌────────────────────────────┐
                            │ JSON Extract & Validation  │
                            │ first {...} + jsonschema   │
                            └──────────┬─────────────────┘
                                       │ 9 summary_json (or fallback w/ error)
                                       ▼
                   ┌───────────────────────────────┐
                   │ Postgres (Document row)       │
                   │ ocr_text, summary_json, status│
                   └──────────┬────────────────────┘
                              │ 10 render detail
                              ▼
                   ┌───────────────────────────────┐
                   │ Client (detail page)          │
                   │ Summary + Raw OCR + Download  │
                   └───────────────────────────────┘




---
## 🚀 Features
- Upload PDFs or images (PNG/JPG/WebP).
- OCR with **PaddleOCR**:
  - Multilingual text recognition
  - Page segmentation
  - Table extraction for lab reports
- Post-processing:
  - Unicode normalization
  - PHI redaction (basic)
- Summarization with **LLMs**:
  - JSON output (summary, highlights, medications, follow-ups, source spans, disclaimer)
- Bootstrap-based simple frontend.

---

## 🛠️ Tech Stack
- **Backend**: Django (Python 3.10+)
- **OCR**: PaddleOCR + PaddlePaddle
- **Summarization**: OpenAI GPT or Hugging Face Qwen
- **Other**: pdf2image, Pillow, NumPy, OpenCV, jsonschema

---

## 📂 Project Structure
-medvault/
-│── manage.py
-│── medvault/ # Django project settings
-│── summarizer/ # OCR + Summarization logic
-│── templates/ # HTML templates
-│── static/ # Static files (CSS/JS)
-│── media/ # Uploaded documents


