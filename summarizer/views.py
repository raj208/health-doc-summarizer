import os, json, uuid, io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings

from .forms import UploadForm
from .models import Document
from .ocr import ocr_file
from .postprocess import redact_phi
from .utils import chunk_text
from .llm import summarize

from django.conf import settings
# ...
if settings.LLM_PROVIDER == 'hf':
    from .llm_hf import summarize as summarize_fn
else:
    from .llm import summarize as summarize_fn

# summarizer/views.py (inside home view)
import traceback
import logging
logger = logging.getLogger(__name__)

def _fail_json(msg, code):
    return {
        "summary": msg,
        "highlights": [],
        "meds": [],
        "followups": [],
        "source_spans": [],
        "disclaimer": "This is not a medical diagnosis.",
        "error": code,
    }


def home(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc: Document = form.save(commit=False)
            doc.original_filename = request.FILES['uploaded_file'].name
            doc.status = 'uploaded'
            doc.save()
            try:
                fullpath = doc.uploaded_file.path

                # 1) OCR
                ocrres = ocr_file(fullpath, doc.language_mode, doc.doc_type)
                combined = []
                for p in ocrres.get('pages', []):
                    body = p.get('text', '') or ''
                    if doc.doc_type == 'labs' and p.get('tables'):
                        body += "\n\n[EXTRACTED_TABLES_AS_HTML]\n" + "\n".join(p['tables'])
                    combined.append(body)
                raw_text = "\n\n--- PAGE BREAK ---\n\n".join(combined).strip()
                redacted = redact_phi(raw_text)
                doc.ocr_text = redacted

                if not redacted:
                    doc.summary_json = _fail_json("No text recognized by OCR. Try English mode or a clearer image.", "empty_ocr")
                    doc.status = 'processed'
                    doc.save()
                    return redirect('detail', pk=doc.id)

                # 2) Chunk
                chunks = chunk_text(redacted, max_tokens=800)
                if not chunks:
                    doc.summary_json = _fail_json("Text parsed but chunking produced no chunks.", "empty_chunks")
                    doc.status = 'processed'
                    doc.save()
                    return redirect('detail', pk=doc.id)

                # 3) LLM (OpenAI or HF)
                from django.conf import settings
                if getattr(settings, "LLM_PROVIDER", "openai") == "hf":
                    from .llm_hf import summarize as summarize_fn
                else:
                    from .llm import summarize as summarize_fn

                meta = {**(ocrres.get('metadata') or {}), "pages_detected": len(ocrres.get('pages', []))}
                result = summarize_fn(meta, chunks)

                # normalize missing fields
                result = {
                    "summary": result.get("summary", "") or "",
                    "highlights": result.get("highlights", []) or [],
                    "meds": result.get("meds", []) or [],
                    "followups": result.get("followups", []) or [],
                    "source_spans": result.get("source_spans", []) or [],
                    "disclaimer": result.get("disclaimer", "This is not a medical diagnosis."),
                    "error": result.get("error", "") or ""
                }

                doc.summary_json = result
                doc.status = 'processed' if not result.get("error") else 'failed'
                doc.save()
                return redirect('detail', pk=doc.id)

            except Exception as e:
                tb = traceback.format_exc()
                logger.exception("Summarization pipeline failed")
                doc.status = 'failed'
                doc.summary_json = _fail_json(getattr(e, "message", None) or repr(e), "exception")
                # include a short traceback when DEBUG=1
                from django.conf import settings
                if settings.DEBUG:
                    doc.summary_json["traceback"] = tb[-4000:]
                doc.save()
                return redirect('detail', pk=doc.id)
    else:
        form = UploadForm()
    return render(request, 'upload.html', {'form': form})


def detail(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    return render(request, 'detail.html', {'doc': doc})

def download_json(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    data = json.dumps(doc.summary_json, ensure_ascii=False, indent=2)
    resp = HttpResponse(data, content_type='application/json; charset=utf-8')
    filename = f"summary_{pk}.json"
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp
