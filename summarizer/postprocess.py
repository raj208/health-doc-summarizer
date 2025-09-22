import re, unicodedata
from langdetect import detect, DetectorFactory
from ftfy import fix_text

DetectorFactory.seed = 0

ZERO_WIDTH = [
    '\u200B','\u200C','\u200D','\u2060','\uFEFF'
]
ZW_RE = re.compile('|'.join(ZERO_WIDTH))

# Very naive PHI redactors (demo only!)
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PHONE_RE = re.compile(r'\b(?:\+\d{1,3}[ -]?)?(?:\d[ -]?){7,12}\b')
DOB_RE = re.compile(r'\b(?:DOB|D\.O\.B\.|Date of Birth)[:\s]*\d{1,2}[-/ ]\d{1,2}[-/ ]\d{2,4}\b', re.I)
MRN_RE = re.compile(r'\b(?:MRN|Patient\s?ID|UHID)[:\s]*[A-Za-z0-9-]+\b', re.I)

def cleanup_unicode(text: str) -> str:
    text = fix_text(text)
    text = unicodedata.normalize('NFKC', text)
    text = ZW_RE.sub('', text)
    text = re.sub(r'[\t\r]+', ' ', text)
    text = re.sub(r'\s+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def redact_phi(text: str) -> str:
    text = EMAIL_RE.sub('[EMAIL]', text)
    text = PHONE_RE.sub('[PHONE]', text)
    text = DOB_RE.sub('[DOB]', text)
    text = MRN_RE.sub('[ID]', text)
    return text

def language_aware_normalize(text: str, lang_mode: str = 'multi') -> str:
    text = cleanup_unicode(text)
    try:
        lang = detect(text) if lang_mode == 'multi' else 'en'
    except Exception:
        lang = 'en'
    # For demo: English just collapse spaces; other langs keep punctuation spacing
    if lang.startswith('en'):
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s*([:;,])\s*', r'\1 ', text)
        text = re.sub(r'\s*\n\s*', '\n', text)
    return text.strip()
