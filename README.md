<!-- # health-doc-summarizer -->
<!-- OCR + LLM-based clinical summarizer built with Django, PaddleOCR, and Hugging Face/OpenAI. -->
# medvault

A Django-based application for extracting and summarizing clinical documents.  
It uses **PaddleOCR** for OCR (English + multilingual, with table extraction for labs) and integrates with **OpenAI** or **Hugging Face (Qwen)** for structured summarization.

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
medvault/
│── manage.py
│── medvault/ # Django project settings
│── summarizer/ # OCR + Summarization logic
│── templates/ # HTML templates
│── static/ # Static files (CSS/JS)
│── media/ # Uploaded documents
