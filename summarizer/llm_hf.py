# summarizer/llm_hf.py
import json
from typing import Dict, Any, List, Optional
from django.conf import settings
from jsonschema import validate
from huggingface_hub import InferenceClient

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "highlights": {"type":"array","items":{"type":"object","properties":{
            "section":{"type":"string"},"text":{"type":"string"}},"required":["section","text"]}},
        "meds": {"type":"array","items":{"type":"object","properties":{
            "name":{"type":"string"},"dose":{"type":"string"},"freq":{"type":"string"}},"required":["name"]}},
        "followups": {"type":"array","items":{"type":"object","properties":{
            "action":{"type":"string"},"timeline":{"type":"string"}},"required":["action"]}},
        "source_spans": {"type":"array","items":{"type":"object","properties":{
            "claim":{"type":"string"},"chunk_ids":{"type":"array","items":{"type":"integer"}}},"required":["claim","chunk_ids"]}},
        "disclaimer": {"type":"string"}
    },
    "required": ["summary","highlights","meds","followups","source_spans","disclaimer"]
}

def _fallback(msg: str, code: str = "") -> Dict[str, Any]:
    return {
        "summary": (msg or "No content returned by the model.")[:900],
        "highlights": [],
        "meds": [],
        "followups": [],
        "source_spans": [],
        "disclaimer": "This is not a medical diagnosis.",
        "error": code,
    }

def _build_messages(metadata: Dict[str, Any], chunks: List[str]) -> List[Dict[str, str]]:
    sys = ("You are a clinical scribe. Summarize only from the provided document chunks. "
           "Do not invent facts. Redact PHI where possible. Respond with ONLY valid JSON that matches the schema.")
    messages = [{"role": "system", "content": sys}]
    messages.append({"role": "user", "content": json.dumps({"document_metadata": metadata}, ensure_ascii=False)})
    messages.append({"role": "user", "content": f"Chunks with IDs: {[i+1 for i in range(len(chunks))]}"} )
    for i, ch in enumerate(chunks, 1):
        messages.append({"role":"user","content": f"Chunk {i}:\n{ch}"})
    messages.append({"role":"user","content":
        "Return ONLY valid JSON with fields: summary, highlights[{section,text}], "
        "meds[{name,dose,freq}], followups[{action,timeline}], "
        "source_spans[{claim,chunk_ids}], disclaimer. No extra text."})
    return messages

def _build_prompt(metadata: Dict[str, Any], chunks: List[str]) -> str:
    header = (
        "You are a clinical scribe. Summarize only from the provided document chunks. "
        "Do not invent facts. Redact PHI where possible.\n\n"
        f"Document metadata: {json.dumps(metadata, ensure_ascii=False)}\n"
        f"Chunks with IDs: {[i+1 for i in range(len(chunks))]}\n\n"
    )
    chunk_text = "\n".join([f"Chunk {i+1}:\n{c}\n" for i, c in enumerate(chunks)])
    contract = ("Return ONLY valid JSON with fields: summary, highlights[{section,text}], "
                "meds[{name,dose,freq}], followups[{action,timeline}], "
                "source_spans[{claim,chunk_ids}], disclaimer. No extra text.")
    return header + chunk_text + "\n" + contract

def _extract_json(s: str) -> Optional[Dict[str, Any]]:
    try:
        start = s.find("{"); end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(s[start:end+1])
            validate(instance=obj, schema=CONTRACT_SCHEMA)
            return obj
    except Exception:
        pass
    return None

def summarize(metadata: Dict[str,Any], chunks: List[str]) -> Dict[str,Any]:
    if not chunks or not any(c.strip() for c in chunks):
        return _fallback("OCR produced no readable text; nothing to summarize.", "empty_ocr")
    if not settings.HF_API_KEY:
        return _fallback("Missing HF_API_KEY. Set it in .env", "missing_api_key")

    client = InferenceClient(model=settings.HF_MODEL_ID, token=settings.HF_API_KEY)

    # 1) Try text-generation first (works for most instruct models)
    prompt = _build_prompt(metadata, chunks)
    try:
        text = client.text_generation(
            prompt,
            max_new_tokens=settings.HF_MAX_NEW_TOKENS,
            temperature=0.2,
            top_p=0.9,
            do_sample=True,
            return_full_text=False,
            seed=getattr(settings, "OPENAI_SEED", 42),
        )
        obj = _extract_json(text)
        if obj is not None:
            return obj
    except Exception as e_text:
        # If provider doesn't support text-generation, we'll fall back to chat below
        last_err = str(e_text)

    # 2) Fallback: use chat_completion (task=conversational, e.g., Cerebras endpoints)
    try:
        messages = _build_messages(metadata, chunks)
        chat = client.chat_completion(
            messages=messages,
            max_tokens=settings.HF_MAX_NEW_TOKENS,   # chat APIs usually use max_tokens
            temperature=0.2,
            top_p=0.9,
            seed=getattr(settings, "OPENAI_SEED", 42),
        )
        # HF chat_completion returns an object with .choices[0].message["content"]
        content = chat.choices[0].message["content"] if chat.choices else ""
        obj = _extract_json(content or "")
        if obj is not None:
            return obj
        return _fallback(content or "Chat completion returned no content.", "json_parse_error")
    except Exception as e_chat:
        return _fallback(f"Hugging Face API error: {e_chat}", "hf_api_error")
