# summarizer/llm_hf.py
import json
from typing import Dict, Any, List, Optional
from django.conf import settings
from jsonschema import validate
from huggingface_hub import InferenceClient

# --- Output contract schema ---
CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "highlights": {"type": "array", "items": {"type":"object","properties":{
            "section":{"type":"string"},"text":{"type":"string"}},"required":["section","text"]}},
        "meds": {"type": "array", "items": {"type":"object","properties":{
            "name":{"type":"string"},"dose":{"type":"string"},"freq":{"type":"string"}},"required":["name"]}},
        "followups": {"type": "array", "items": {"type":"object","properties":{
            "action":{"type":"string"},"timeline":{"type":"string"}},"required":["action"]}},
        "source_spans": {"type": "array", "items": {"type":"object","properties":{
            "claim":{"type":"string"},"chunk_ids":{"type":"array","items":{"type":"integer"}}},"required":["claim","chunk_ids"]}},
        "disclaimer": {"type": "string"}
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

# --- Qwen ChatML formatting ---
# Qwen expects ChatML-like tags:
# <|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n
def _chatml_qwen(system_prompt: str, user_turns: List[str]) -> str:
    parts = []
    parts.append("<|im_start|>system\n" + system_prompt.strip() + "\n<|im_end|>")
    for u in user_turns:
        parts.append("<|im_start|>user\n" + u.strip() + "\n<|im_end|>")
    # The assistant tag is the generation start
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)

def _extract_json(s: str) -> Optional[Dict[str, Any]]:
    # Grab the first {...} block; validate against contract
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

    client = InferenceClient(token=settings.HF_API_KEY)

    system_prompt = (
        "You are a clinical scribe. Summarize only from the provided document chunks. "
        "Do not invent facts. Redact PHI where possible. Respond with ONLY valid JSON matching the schema."
    )

    # Build the 'user' content: doc metadata + chunks + contract reminder
    user_msgs = []
    user_msgs.append("Document metadata: " + json.dumps(metadata, ensure_ascii=False))
    user_msgs.append("Chunks with IDs: " + json.dumps([i+1 for i in range(len(chunks))]))
    for i, ch in enumerate(chunks, 1):
        user_msgs.append(f"Chunk {i}:\n{ch}")
    user_msgs.append(
        "Return ONLY valid JSON with fields: "
        "summary, highlights[{section,text}], meds[{name,dose,freq}], "
        "followups[{action,timeline}], source_spans[{claim,chunk_ids}], disclaimer. "
        "No extra text."
    )

    prompt = _chatml_qwen(system_prompt, user_msgs)

    try:
        # Use text generation; Qwen understands ChatML prompt above
        text = client.text_generation(
            prompt=prompt,
            model=settings.HF_MODEL_ID,             # ensure we target Qwen
            max_new_tokens=settings.HF_MAX_NEW_TOKENS,
            temperature=0.2,
            top_p=0.9,
            do_sample=True,                         # set False if you prefer more determinism
            return_full_text=False,
            # Some backends honor seed; harmless if ignored
            seed=getattr(settings, "OPENAI_SEED", 42),
        )
    except Exception as e:
        return _fallback(f"Hugging Face API error: {e}", "hf_api_error")

    obj = _extract_json(text or "")
    if obj is not None:
        return obj

    # Last resort: return raw as summary
    return _fallback(text or "Empty model response", "json_parse_error")
