from fastapi import APIRouter, Body, HTTPException
from typing import Any, Dict
import os, json, tempfile, shutil
from datetime import datetime, timezone

router = APIRouter(prefix="/home", tags=["home"])

# ---- JSON location ----
DATA_DIR = os.path.join("storage", "content")
HOME_JSON = os.path.join(DATA_DIR, "home.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# ---- constants ----
SECTIONS = {"hero", "steps", "features", "testimonials", "trusted_by", "theme"}
DEFAULT_CONTENT: Dict[str, Any] = {
    "theme": {"brand_teal": "#21c7b8"},
    "hero": {
        "title": "",
        "subtitle": "",
        "image": {"url": "", "alt": ""},
        "points": [],
        "ctas": []  # [{label, href, variant}]
    },
    "steps": {
        "title": "",
        "items": []  # [{icon, title, desc}]
    },
    "features": {
        "title": "",
        "subtitle": "",
        "cards": []  # [{badge, icon, title, desc, bullets, href}]
    },
    "testimonials": {
        "title": "",
        "per_page_desktop": 3,
        "items": []  # [{quote, name, role, avatar}]
    },
    "trusted_by": {
        "title": "TRUSTED BY",
        "avatars": []  # [url, ...]
    },
}

# ---- helpers ----
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def _init_if_missing():
    _ensure_dirs()
    if not os.path.exists(HOME_JSON):
        data = {
            "meta": {"version": 1, "generated_at": _now_iso(), "page": "home"},
            "content": DEFAULT_CONTENT.copy(),
        }
        _atomic_save(data)

def _load() -> Dict[str, Any]:
    _init_if_missing()
    with open(HOME_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def _backup():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(HOME_JSON, os.path.join(BACKUP_DIR, f"home-{ts}.json"))

def _atomic_save(data: Dict[str, Any]):
    data["meta"] = data.get("meta", {})
    data["meta"]["generated_at"] = _now_iso()
    # Also bump updated_at for convenience
    data["meta"]["updated_at"] = _now_iso()
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="home-", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, HOME_JSON)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

def _get_content(data: Dict[str, Any]) -> Dict[str, Any]:
    content = data.get("content") or {}
    # Ensure all default top-level keys exist
    for k, v in DEFAULT_CONTENT.items():
        if k not in content:
            content[k] = json.loads(json.dumps(v))  # deep copy
    return content

def _coerce_section_shape(section: str, obj: Any) -> Dict[str, Any]:
    """Make a best-effort to coerce the section payload into the expected shape."""
    if section not in SECTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown section '{section}'")

    # Accept either {section: {...}} or a raw object {...}
    if isinstance(obj, dict) and section in obj and isinstance(obj[section], dict):
        payload = obj[section]
    else:
        if not isinstance(obj, dict):
            raise HTTPException(status_code=400, detail="Payload must be an object")
        payload = obj

    # Light defaults/normalization per section
    if section == "theme":
        payload.setdefault("brand_teal", "#21c7b8")

    elif section == "hero":
        payload.setdefault("title", "")
        payload.setdefault("subtitle", "")
        payload.setdefault("image", {})
        payload["image"].setdefault("url", "")
        payload["image"].setdefault("alt", "")
        payload.setdefault("points", [])
        payload.setdefault("ctas", [])
        # normalize CTAs: {label, href, variant}
        if isinstance(payload["ctas"], list):
            norm = []
            for c in payload["ctas"]:
                if not isinstance(c, dict): 
                    continue
                norm.append({
                    "label": c.get("label", ""),
                    "href": c.get("href", c.get("to", "")),
                    "variant": c.get("variant", c.get("style", "primary")),
                })
            payload["ctas"] = norm

    elif section == "steps":
        payload.setdefault("title", "")
        payload.setdefault("items", [])
        if isinstance(payload["items"], list):
            norm = []
            for s in payload["items"]:
                if not isinstance(s, dict):
                    continue
                norm.append({
                    "icon": s.get("icon", "upload"),
                    "title": s.get("title", ""),
                    "desc": s.get("desc", s.get("description", "")),
                })
            payload["items"] = norm

    elif section == "features":
        payload.setdefault("title", "")
        payload.setdefault("subtitle", "")
        payload.setdefault("cards", [])
        if isinstance(payload["cards"], list):
            norm = []
            for f in payload["cards"]:
                if not isinstance(f, dict):
                    continue
                bullets = f.get("bullets", [])
                if not isinstance(bullets, list):
                    bullets = []
                norm.append({
                    "badge": f.get("badge", "Core"),
                    "icon": f.get("icon", "shield"),
                    "title": f.get("title", ""),
                    "desc": f.get("desc", f.get("description", "")),
                    "bullets": [str(b).strip() for b in bullets if str(b).strip()],
                    "href": f.get("href", f.get("learn_more_to", "#")),
                })
            payload["cards"] = norm

    elif section == "testimonials":
        payload.setdefault("title", "")
        ppd = payload.get("per_page_desktop")
        if not isinstance(ppd, int) or ppd < 1:
            payload["per_page_desktop"] = 3
        payload.setdefault("items", [])
        if isinstance(payload["items"], list):
            norm = []
            for t in payload["items"]:
                if not isinstance(t, dict):
                    continue
                norm.append({
                    "quote": t.get("quote", ""),
                    "name": t.get("name", ""),
                    "role": t.get("role", ""),
                    "avatar": t.get("avatar", ""),
                })
            payload["items"] = norm

    elif section == "trusted_by":
        payload.setdefault("title", "TRUSTED BY")
        avatars = payload.get("avatars", [])
        if not isinstance(avatars, list):
            avatars = []
        payload["avatars"] = [str(u) for u in avatars if str(u).strip()]

    return payload

def _save_sections(partial_content: Dict[str, Any]) -> Dict[str, Any]:
    """Merge provided sections into content and save atomically."""
    data = _load()
    content = _get_content(data)

    changed = False
    for k, v in partial_content.items():
        if k not in SECTIONS:
            continue
        coerced = _coerce_section_shape(k, v if isinstance(v, dict) else {k: v})
        if content.get(k) != coerced:
            content[k] = coerced
            changed = True

    if not changed:
        # still bump meta updated_at to reflect an explicit save
        data["meta"] = data.get("meta", {})
        data["meta"]["updated_at"] = _now_iso()
        _atomic_save({"meta": data["meta"], "content": content})
        return {"meta": data["meta"], "content": content}

    new_data = {"meta": data.get("meta", {}), "content": content}
    _backup()
    _atomic_save(new_data)
    return new_data

# ---- ROUTES ----

@router.get("/", summary="Get Home page JSON")
def get_home():
    print("[GET] /home called")
    return _load()

@router.put("/", summary="Update Home page JSON")
def update_home(payload: Dict[str, Any] = Body(...)):
    """
    Replace or update Home page JSON content.
    Accepts either full {meta, content} or a raw content object.
    """
    print("[PUT] /home payload =", payload)

    if "content" in payload:
        new_data = {
            "meta": payload.get("meta") or _load().get("meta", {}),
            "content": _get_content({"content": payload["content"]}),
        }
    else:
        new_data = {
            "meta": payload.get("meta") or _load().get("meta", {}),
            "content": _get_content({"content": payload}),
        }

    _backup()
    _atomic_save(new_data)
    return new_data

# ---- META ROUTES ----
@router.get("/meta", summary="Get meta block")
def get_meta():
    data = _load()
    return data.get("meta", {})

@router.put("/meta", summary="Update meta block")
def put_meta(meta: Dict[str, Any] = Body(...)):
    data = _load()
    data["meta"] = {**(data.get("meta", {})), **(meta or {})}
    _backup()
    _atomic_save(data)
    return data["meta"]

# ---- GENERIC SECTION ROUTES ----
def _ensure_section_exists(section: str):
    if section not in SECTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown section '{section}'")

@router.get("/{section}", summary="Get a single section by key")
def get_section(section: str):
    _ensure_section_exists(section)
    data = _load()
    content = _get_content(data)
    return content.get(section, DEFAULT_CONTENT[section])

@router.put("/{section}", summary="Put/merge a single section by key")
def put_section(section: str, body: Dict[str, Any] = Body(...)):
    """
    Update only one section (hero/steps/features/testimonials/trusted_by/theme).
    Body may be either the raw object or { "<section>": { … } }.
    """
    _ensure_section_exists(section)
    payload = {section: body}
    saved = _save_sections(payload)
    # return the updated section only (nice for UI), but you can return saved if you prefer
    return saved["content"][section]

# ---- Convenience explicit routes (optional, clearer OpenAPI) ----
@router.get("/hero", include_in_schema=False)
def _get_hero():
    return get_section("hero")

@router.put("/hero", include_in_schema=False)
def _put_hero(body: Dict[str, Any] = Body(...)):
    return put_section("hero", body)

@router.get("/steps", include_in_schema=False)
def _get_steps():
    return get_section("steps")

@router.put("/steps", include_in_schema=False)
def _put_steps(body: Dict[str, Any] = Body(...)):
    return put_section("steps", body)

@router.get("/features", include_in_schema=False)
def _get_features():
    return get_section("features")

@router.put("/features", include_in_schema=False)
def _put_features(body: Dict[str, Any] = Body(...)):
    return put_section("features", body)

@router.get("/testimonials", include_in_schema=False)
def _get_testimonials():
    return get_section("testimonials")

@router.put("/testimonials", include_in_schema=False)
def _put_testimonials(body: Dict[str, Any] = Body(...)):
    return put_section("testimonials", body)

@router.get("/trusted_by", include_in_schema=False)
def _get_trusted_by():
    return get_section("trusted_by")

@router.put("/trusted_by", include_in_schema=False)
def _put_trusted_by(body: Dict[str, Any] = Body(...)):
    return put_section("trusted_by", body)

@router.get("/theme", include_in_schema=False)
def _get_theme():
    return get_section("theme")

@router.put("/theme", include_in_schema=False)
def _put_theme(body: Dict[str, Any] = Body(...)):
    return put_section("theme", body)
