<!-- # health-doc-summarizer -->
<!-- OCR + LLM-based clinical summarizer built with Django, PaddleOCR, and Hugging Face/OpenAI. -->
# medvault

A Django-based application for extracting and summarizing clinical documents.  
It uses **PaddleOCR** for OCR (English + multilingual, with table extraction for labs) and integrates with **OpenAI** or **Hugging Face (Qwen)** for structured summarization.

---
## Architecture Overview
┌────────────┐          1. HTTP POST /upload           ┌────────────────────────────┐
│   Client   │ ───────────────────────────────────────▶│ Django View: /upload        │
│  (Web UI)  │ ◀────────── 2. HTML (detail link) ──────┘                            │
└────────────┘                                                │
                                                             ▼
                                               create Document(status='uploaded')
                                               ├─ Save file → MEDIA/uploads/...
                                               ├─ Compute file_hash (SHA256)
                                               └─ Check cache by file_hash
                                                             │
                                                             ▼
                                        ┌────────────────────────────────┐
                                        │   Object Store (Local Files)   │
                                        │   Stores original uploaded doc │
                                        └────────────────┬───────────────┘
                                                         │
                          4. Load/convert images or rasterize PDF
                                                         ▼
                                 ┌────────────────────────────────────┐
                                 │   Preprocessing (Image Variants)   │
                                 │   CLAHE, Thresholding, Upscaling   │
                                 └────────────────┬───────────────────┘
                                                  │ For each variant:
                                                  ▼
                                  ┌────────────────────────────────────┐
                                  │    PaddleOCR (det + cls + rec)     │
                                  │ + PP-Structure (layout analysis)   │
                                  └────────────────┬───────────────────┘
                                                  │
                       5. Extracted text lines (and optional table HTML)
                                                  ▼
                                  ┌────────────────────────────────────┐
                                  │   Post-processing + PHI Redaction  │
                                  │   Unicode NFKC, ftfy, ZWSP remove  │
                                  └────────────────┬───────────────────┘
                                                  │
                                   6. Cleaned OCR text (`cleaned_text`)
                                                  ▼
                                  ┌────────────────────────────────────┐
                                  │   Chunker: Token-Aware Splitting   │
                                  │   Generates IDs, overlap windows   │
                                  └────────────────┬───────────────────┘
                                                  │
                                         7. Text Chunks (`chunks[]`)
                                                  ▼
                         ┌─────────────────────────────────────────────┐
                         │       Summarizer (LLM options):             │
                         │       a) OpenAI Chat (JSON-mode)            │
                         │       b) HF Qwen (via Inference API)        │
                         └────────────────┬────────────────────────────┘
                                          │
                                 8. Raw model response (`raw_model_text`)
                                          ▼
                            ┌──────────────────────────────────────────┐
                            │   JSON Extraction & Schema Validation    │
                            │   Use `json.loads()` + `jsonschema`      │
                            └────────────────┬─────────────────────────┘
                                          │
                          9. Final `summary_json` (or fallback error)
                                          ▼
                    ┌──────────────────────────────────────────────┐
                    │ PostgreSQL `Document` row update             │
                    │ Stores: `ocr_text`, `summary_json`, `status` │
                    └────────────────┬─────────────────────────────┘
                                     │
                            10. Render detail page
                                     ▼
                    ┌──────────────────────────────────────────────┐
                    │    Client (Document Detail View)             │
                    │    View Summary + Raw OCR + Download Option  │
                    └──────────────────────────────────────────────┘




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

📂 medvault/                     # Root project directory
├── manage.py                   # Django management script
├── medvault/                   # Django project settings and configuration
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── summarizer/                 # App containing OCR and summarization logic
│   ├── __init__.py
│   ├── views.py
│   ├── models.py
│   ├── urls.py
│   └── utils/                  # (Optional) OCR and summarization helper modules
├── templates/                  # HTML templates for rendering views
│   └── *.html
├── static/                     # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
├── media/                      # Uploaded user documents (PDFs, images, etc.)
│   └── uploads/



