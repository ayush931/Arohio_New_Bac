# app/api/v1/routes_ai_chat.py
from fastapi import APIRouter, HTTPException, Body
import json, os, re, urllib.request, urllib.error
from urllib.parse import urljoin

router = APIRouter(prefix="/ai", tags=["AI Chat (Ollama)"])

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")

def _http_get(path: str):
    url = urljoin(OLLAMA_HOST, path)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8") if e.fp else str(e)
        raise HTTPException(status_code=e.code, detail=f"{url}: {detail}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"{url}: {e}")

def _http_post(path: str, payload: dict):
    url = urljoin(OLLAMA_HOST, path)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8") if e.fp else str(e)
        raise HTTPException(status_code=e.code, detail=f"{url}: {detail}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"{url}: {e}")

@router.get("/health")
def health():
    _ = _http_get("/api/version")
    return {"ok": True}

@router.get("/models")
def models():
    data = _http_get("/api/tags")
    names = [m.get("name") for m in data.get("models", [])]
    return {"ok": True, "models": names}

# ------------------- GUARDS & CONSTANTS -------------------

BLOCK_RE = re.compile(
    r"(porn|porno|nsfw|nude|nudity|erotic|sex(ual|y)?|fuck|boob|breast|penis|vagina|strip\s*club|night\s*club)",
    re.IGNORECASE,
)

PRODUCT_FACTS = (
    "Arohio helps teams create high-quality ALT TEXT in English. Core capabilities: "
    "1) PDF→image extraction and per-image management; "
    "2) PDF→Alt Text generation (per image) with regenerate and edit; "
    "3) Images→Alt Text (direct image upload); "
    "4) Excel/CSV/XLSX→Alt Text (bulk) using image paths/URLs; "
    "5) Export results to JSON/CSV/XLSX; "
    "6) Team review/collaboration. "
    "Not supported: general language translation, voice translation, speech-to-text, or text-to-speech."
)

SYSTEM_PROMPT = (
    "You are Arohio's virtual assistant. Always answer in English (en-GB). "
    "Only use the Product Facts provided. If the user asks for features not in Product Facts, say they are not supported and offer supported workflows. "
    f"Product Facts: {PRODUCT_FACTS} "
    "Response policy: "
    "Be concise, friendly, and professional. Prefer clear numbered steps for how-to questions. "
    "Stay strictly within WCAG, alt text, accessibility, or Arohio workflows. "
    "If out of scope, reply exactly: "
    "Sorry, I can help with WCAG, alt text, accessibility, or Arohio workflows only. Please ask a question in that scope. "
    "Never mention vendors, models, or LLMs."
)

VENDOR_WORDS_RE = re.compile(
    r"\b(chatgpt|openai|gpt[- ]?\d+(?:\.\d+)?|llm|large language model|generative pretrained transformer|anthropic|claude|gemini|llava|ollama|model)\b",
    re.IGNORECASE,
)

# Expanded small talk detection (covers hy/hii/hyy/yo/gm/gn/namaste/etc.)
SMALLTALK_RE = re.compile(
    r"""^\s*(
        h(i+|y+|ey+|iya)?|
        hello(\s*there)?|
        hey(\s*there)?|
        yo+|
        sup|what'?s\s*up|wassup|wazzup|
        gm|good\s*morning|gn|good\s*night|good\s*evening|good\s*afternoon|
        namaste|namaskar|salaam|salam
    )\b.*$""",
    re.IGNORECASE | re.VERBOSE,
)

TRANSLATION_CLAIM_RE = re.compile(
    r"\b(translate|translation|voice\s*translation|speech\s*to\s*text|text\s*to\s*speech|tts|stt|over\s*\d+\s*languages|near-?human\s*accuracy)\b",
    re.IGNORECASE,
)

ABOUT_AROHIO_RE = re.compile(
    r"\b(what\s+is|what'?s|tell\s+me\s+about|about)\s+(arohio|arroyo|aroyo|arrohio)\b|\b(arohio|arroyo|aroyo|arrohio)\s*\?$",
    re.IGNORECASE,
)

# Deterministic detectors
ALT_TEXT_DEF_RE = re.compile(
    r"\b(what\s+is|what'?s|define|meaning\s+of)\s+(alt[-\s]*text|alt\s*tag|alternative\s*text)\b",
    re.IGNORECASE,
)
PDF_INTENT_RE = re.compile(r"\b(pdf|\.pdf)\b", re.IGNORECASE)
EXCEL_INTENT_RE = re.compile(r"\b(excel|xlsx|csv|spreadsheet|manifest)\b", re.IGNORECASE)
IMAGE_INTENT_RE = re.compile(r"\b(image|images|jpg|jpeg|png|gif|tiff)\b", re.IGNORECASE)
STEPSY_RE = re.compile(r"\b(how\s+do\s+i|how\s+to|steps|convert|create|generate|make)\b", re.IGNORECASE)

RESPONSE_TEMPLATES = {
    "greeting": (
        "Hi there! I’m Arohio's virtual assistant. I can help you create high-quality alt text. "
        "Would you like to start with a PDF, an Excel sheet, or direct images?"
    ),
    "about": (
        "Arohio is an accessibility workspace for creating high-quality alt text. "
        "It lets you: 1) extract images from PDFs, 2) generate and edit per-image alt text, "
        "3) bulk create alt text from Excel/CSV/XLSX using image paths or URLs, "
        "4) export results to JSON/CSV/XLSX, 5) review with your team. "
        "Would you like to start with a PDF or an Excel sheet?"
    ),
    "alt_def": (
        "Alt text is a short, accurate description of an image for people who use screen readers and for cases where images don’t load. "
        "In Arohio, you can generate and manage alt text per image, review it, edit for clarity, and export the results. "
        "Steps to get started: "
        "1) Choose a workflow: PDF, Excel, or direct images. "
        "2) Generate alt text for each image. "
        "3) Review and refine. "
        "4) Export to JSON/CSV/XLSX for your project. "
        "Ready to try a PDF or an Excel sheet?"
    ),
    "pdf_steps": (
        "Here’s how to convert a PDF to alt text in Arohio: "
        "1) Upload your PDF. "
        "2) Arohio extracts all images from the PDF. "
        "3) Click Generate Alt Text to create descriptions per image. "
        "4) Review and edit the text for accuracy and context. "
        "5) Export your results to JSON/CSV/XLSX. "
        "Would you like to upload a PDF now?"
    ),
    "excel_steps": (
        "Here’s how to create alt text from an Excel/CSV in Arohio: "
        "1) Prepare a sheet with an image_path or image_url column; add optional context columns if helpful. "
        "2) Upload the Excel/CSV/XLSX. "
        "3) Click Generate Alt Text to create entries for each row. "
        "4) Review and edit the results. "
        "5) Export to JSON/CSV/XLSX. "
        "Do you have a sheet ready to upload?"
    ),
    "image_steps": (
        "Here’s how to generate alt text for direct images: "
        "1) Upload your images (JPG, PNG, etc.). "
        "2) Click Generate Alt Text to produce descriptions for each image. "
        "3) Review and refine the wording. "
        "4) Export the final set to JSON/CSV/XLSX. "
        "Want to upload a few images to begin?"
    ),
    "unsupported": (
        "Arohio is not a general translation or voice/TTS platform. "
        "It focuses on accessibility: extracting images from PDFs, generating alt text, and handling Excel/CSV/XLSX alt-text workflows with export and team review. "
        "Would you like to generate alt text from a PDF or an Excel sheet?"
    ),
    "fallback": (
        "I can help with alt text and Arohio workflows. "
        "Would you like step-by-step guidance for a PDF, an Excel sheet, or direct images?"
    ),
}

# ------------------- HELPERS -------------------

def _looks_non_english(text: str) -> bool:
    return bool(re.search(r"[^\x00-\x7F]", text))

def _clean_text(text: str) -> str:
    text = re.sub(r"[*_`#>\[\]]+", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.replace("•", "-")
    return text.strip()

def _non_disclosure_message() -> str:
    return "I’m Arohio's virtual assistant. We don’t share vendor or model details; I can help with accessibility and Arohio workflows."

def _apply_vendor_guard(user_text: str, reply_text: str) -> str:
    if VENDOR_WORDS_RE.search(user_text or ""):
        return _non_disclosure_message()
    if VENDOR_WORDS_RE.search(reply_text or ""):
        return _non_disclosure_message()
    return reply_text

def _intent_hint(user_text: str) -> str:
    t = (user_text or "").lower()
    if "alt text" in t or "alt-text" in t or "alttext" in t or "what do you mean by alt" in t:
        return "Focus on defining alt text and then Arohio's alt-text generation workflow with steps and a short CTA."
    if "pdf" in t:
        return "Focus on Arohio's PDF to Alt Text workflow with numbered steps."
    if "excel" in t or "xlsx" in t or "spreadsheet" in t or "manifest" in t:
        return "Focus on Arohio's Excel to Alt Text workflow with numbered steps."
    if "arohio" in t or "feature" in t or "capabilit" in t or "what can you do" in t:
        return "Describe Arohio's capabilities from Product Facts and invite the user to try a feature."
    return "Answer strictly within accessibility, WCAG, alt text, and Arohio workflows."

def _shorten(reply: str, max_chars: int = 800) -> str:
    r = reply.strip()
    if len(r) <= max_chars:
        return r
    lines = r.splitlines()
    kept, total = [], 0
    for i, line in enumerate(lines):
        if not line.strip():
            if total + 1 > max_chars: break
            kept.append(""); total += 1; continue
        if re.match(r"\s*\d+[\.\)]\s", line):
            if total + len(line) + 1 > max_chars: break
            kept.append(line); total += len(line) + 1; continue
        if i == 0 or not kept:
            if total + len(line) + 1 > max_chars: break
            kept.append(line); total += len(line) + 1; continue
        if re.search(r":\s*$", kept[-1]) and re.match(r"\s*\d+[\.\)]\s", line):
            if total + len(line) + 1 > max_chars: break
            kept.append(line); total += len(line) + 1; continue
        if total + len(line) + 1 > max_chars: break
        kept.append(line); total += len(line) + 1
    if kept:
        return "\n".join(kept).strip()
    cut = r[:max_chars]
    last_nl = cut.rfind("\n")
    if last_nl > 200:
        return cut[:last_nl].strip()
    last_dot = cut.rfind(". ")
    if last_dot > 200:
        return (cut[: last_dot + 1]).strip()
    return cut.strip()

def _apply_fact_guard(user_text: str, reply_text: str) -> str:
    if TRANSLATION_CLAIM_RE.search(user_text or "") or TRANSLATION_CLAIM_RE.search(reply_text or ""):
        return RESPONSE_TEMPLATES["unsupported"]
    return reply_text

def _about_arohio_response() -> str:
    return RESPONSE_TEMPLATES["about"]

def _inject_arohio_context(user_text: str, reply: str) -> str:
    reply = _clean_text(reply)
    reply = _shorten(reply, max_chars=800)
    if "arohio" not in reply.lower():
        reply = reply + " — Powered by Arohio's Virtual Assistant"
    return reply

# Extra: tiny heuristic so 1–4 char salutations (“hy”, “hi”, “yo”) count as greeting
def _looks_like_short_greeting(t: str) -> bool:
    s = (t or "").strip().lower()
    if not s:
        return False
    if len(s) <= 4 and re.fullmatch(r"[a-z\s!?.]+", s or ""):
        # common first-letter patterns
        return s.startswith(("h", "y")) or s in {"yo", "gm", "gn", "gm!", "gn!"}
    return False

# Deterministic router
def _deterministic_reply(user_text: str):
    t = (user_text or "").strip()
    if not t:
        return None

    if _looks_like_short_greeting(t) or SMALLTALK_RE.match(t):
        return RESPONSE_TEMPLATES["greeting"]

    if ABOUT_AROHIO_RE.search(t):
        return RESPONSE_TEMPLATES["about"]

    if ALT_TEXT_DEF_RE.search(t):
        return RESPONSE_TEMPLATES["alt_def"]

    if TRANSLATION_CLAIM_RE.search(t):
        return RESPONSE_TEMPLATES["unsupported"]

    if STEPSY_RE.search(t):
        if PDF_INTENT_RE.search(t):
            return RESPONSE_TEMPLATES["pdf_steps"]
        if EXCEL_INTENT_RE.search(t):
            return RESPONSE_TEMPLATES["excel_steps"]
        if IMAGE_INTENT_RE.search(t):
            return RESPONSE_TEMPLATES["image_steps"]
        return RESPONSE_TEMPLATES["fallback"]

    if PDF_INTENT_RE.search(t):
        return RESPONSE_TEMPLATES["pdf_steps"]
    if EXCEL_INTENT_RE.search(t):
        return RESPONSE_TEMPLATES["excel_steps"]
    if IMAGE_INTENT_RE.search(t):
        return RESPONSE_TEMPLATES["image_steps"]

    return None

# ------------------- ENDPOINT -------------------

@router.post("/chat")
def chat(
    body: dict = Body(..., example={
        "message": "How do I convert a PDF to alt text in Arohio?",
        "model": DEFAULT_MODEL,
        "system": SYSTEM_PROMPT,
        "options": {"temperature": 0.2}
    })
):
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="message is required")

    if BLOCK_RE.search(message):
        return {
            "ok": True,
            "model": body.get("model") or DEFAULT_MODEL,
            "reply": "Sorry, this request contains disallowed terms. Please ask about WCAG, alt text, accessibility, or Arohio workflows."
        }

    # Deterministic, human reply path first
    det = _deterministic_reply(message)
    if det:
        det = _apply_vendor_guard(message, det)
        det = _apply_fact_guard(message, det)
        det = _inject_arohio_context(message, det)
        if _looks_non_english(det):
            det = det.encode("ascii", "ignore").decode("ascii")
        return {"ok": True, "model": DEFAULT_MODEL, "reply": det}

    # Fallback to model for unclear intents
    model = body.get("model") or DEFAULT_MODEL
    system = body.get("system") or SYSTEM_PROMPT
    options = body.get("options") or {}

    intent = _intent_hint(message)
    dynamic_system = f"{system}\n\nUSER INTENT HINT\n• {intent}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": dynamic_system},
            {"role": "user", "content": message},
        ],
        "stream": False,
        "options": options,
    }

    data = _http_post("/api/chat", payload)
    content = (data.get("message") or {}).get("content", "").strip()
    if not content:
        raise HTTPException(status_code=500, detail="Empty response from Ollama")

    content = _apply_vendor_guard(message, content)
    content = _apply_fact_guard(message, content)
    content = _inject_arohio_context(message, content)

    if _looks_non_english(content):
        content = content.encode("ascii", "ignore").decode("ascii")

    return {"ok": True, "model": model, "reply": content}
