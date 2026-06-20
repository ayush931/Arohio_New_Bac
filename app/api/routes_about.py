# app/api/v1/routes_about.py
from fastapi import APIRouter, Body, HTTPException, status
from typing import Any, Dict, List, Optional
import os, json, tempfile, shutil
from datetime import datetime, timezone

router = APIRouter(prefix="/about", tags=["about"])

DATA_DIR = os.path.join("storage", "content")
ABOUT_JSON = os.path.join(DATA_DIR, "about.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def _atomic_save(data: Dict[str, Any]):
    data["meta"] = data.get("meta", {})
    data["meta"]["updated_at"] = _now_iso()
    fd, tmp = tempfile.mkstemp(prefix="about-", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ABOUT_JSON)
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass

def _backup():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    if os.path.exists(ABOUT_JSON):
        shutil.copy2(ABOUT_JSON, os.path.join(BACKUP_DIR, f"about-{ts}.json"))

def _init_if_missing():
    _ensure_dirs()
    if not os.path.exists(ABOUT_JSON):
        data = {
            "meta": {"version": 1, "updated_at": _now_iso(), "locale": "en"},
            "hero": {
                "title": "About Arohio",
                "lead": "",
                "body": "",
                "image": {"url": "", "alt": "", "overlay": "dark"},
                "ctas": [],
                "highlights": [],
                "visible": True
            },
            "sections": []
        }
        _atomic_save(data)

def _load() -> Dict[str, Any]:
    _init_if_missing()
    with open(ABOUT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def _find_section(data: Dict[str, Any], sec_id: str) -> Optional[Dict[str, Any]]:
    return next((s for s in data.get("sections", []) if s.get("id") == sec_id), None)

def _validate_section(s: Dict[str, Any]):
    t = s.get("type")
    if not s.get("id"): raise HTTPException(400, detail="Section id required")
    if t not in {"card","card_grid","split","team_grid"}: raise HTTPException(400, detail="Invalid section type")
    if t in {"card","card_grid","split","team_grid"} and not s.get("title") and t != "team_grid":
        raise HTTPException(400, detail="Title required")
    s["visible"] = bool(s.get("visible", True))

def _validate_all(data: Dict[str, Any]):
    h = data.get("hero", {})
    if h.get("visible", True) and not h.get("title"):
        raise HTTPException(400, detail="Hero title required")
    ids = []
    for s in data.get("sections", []):
        _validate_section(s)
        if s["id"] in ids: raise HTTPException(400, detail=f"Duplicate section id: {s['id']}")
        ids.append(s["id"])

@router.get("/", status_code=status.HTTP_200_OK)
def get_about():
    print("[GET] /about")
    return _load()

@router.put("/", status_code=status.HTTP_200_OK)
def put_about(payload: Dict[str, Any] = Body(...)):
    print("[PUT] /about")
    data = _load()
    merged = {
        "meta": payload.get("meta") or data.get("meta") or {},
        "hero": payload.get("hero") or data.get("hero") or {},
        "sections": payload.get("sections") or data.get("sections") or []
    }
    _validate_all(merged)
    _backup()
    _atomic_save(merged)
    return merged

@router.post("/sections", status_code=status.HTTP_201_CREATED)
def add_section(section: Dict[str, Any] = Body(...)):
    print("[POST] /about/sections", section.get("id"))
    data = _load()
    _validate_section(section)
    if _find_section(data, section["id"]):
        raise HTTPException(400, detail="Section id already exists")
    data.setdefault("sections", []).append(section)
    _backup()
    _atomic_save(data)
    return section

@router.put("/sections/{sec_id}", status_code=status.HTTP_200_OK)
def update_section(sec_id: str, patch: Dict[str, Any] = Body(...)):
    print("[PUT] /about/sections/", sec_id)
    data = _load()
    sec = _find_section(data, sec_id)
    if not sec: raise HTTPException(404, detail="Section not found")
    for k, v in patch.items():
        if v is not None:
            sec[k] = v
    _validate_section(sec)
    _backup()
    _atomic_save(data)
    return sec

@router.delete("/sections/{sec_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(sec_id: str):
    print("[DELETE] /about/sections/", sec_id)
    data = _load()
    before = len(data.get("sections", []))
    data["sections"] = [s for s in data.get("sections", []) if s.get("id") != sec_id]
    if len(data["sections"]) == before:
        raise HTTPException(404, detail="Section not found")
    _backup()
    _atomic_save(data)
    return None

@router.put("/sections/reorder", status_code=status.HTTP_200_OK)
def reorder_sections(order: List[str] = Body(..., embed=True)):
    print("[PUT] /about/sections/reorder", order)
    data = _load()
    by_id = {s["id"]: s for s in data.get("sections", [])}
    new_list = []
    for sid in order:
        if sid in by_id:
            new_list.append(by_id.pop(sid))
    for rest in by_id.values():
        new_list.append(rest)
    data["sections"] = new_list
    _backup()
    _atomic_save(data)
    return {"sections": data["sections"]}

@router.patch("/hero", status_code=status.HTTP_200_OK)
def patch_hero(patch: Dict[str, Any] = Body(...)):
    print("[PATCH] /about/hero")
    data = _load()
    hero = data.get("hero", {})
    for k, v in patch.items():
        if v is not None:
            if k == "image" and isinstance(v, dict):
                img = hero.get("image", {})
                img.update(v)
                hero["image"] = img
            else:
                hero[k] = v
    data["hero"] = hero
    _validate_all(data)
    _backup()
    _atomic_save(data)
    return hero
