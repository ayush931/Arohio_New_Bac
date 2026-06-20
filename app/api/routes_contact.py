from fastapi import APIRouter, Body, HTTPException, status
from typing import Any, Dict
import os, json, tempfile, shutil
from datetime import datetime, timezone

router = APIRouter(prefix="/contact", tags=["contact"])

DATA_DIR = os.path.join("storage", "content")
CONTACT_JSON = os.path.join(DATA_DIR, "contact.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def _atomic_save(data: Dict[str, Any]):
    fd, tmp = tempfile.mkstemp(prefix="contact-", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONTACT_JSON)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except:
                pass

def _backup():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    if os.path.exists(CONTACT_JSON):
        shutil.copy2(CONTACT_JSON, os.path.join(BACKUP_DIR, f"contact-{ts}.json"))

def _init_if_missing():
    _ensure_dirs()
    if not os.path.exists(CONTACT_JSON):
        data = {
            "meta": {"version": 1, "updated_at": _now_iso(), "locale": "en"},
            "hero": {
                "title": "Need help? We’re here for you.",
                "lead": "Our team is dedicated to providing the best possible support."
            },
            "form": {
                "title": "Send us a message",
                "fields": [],
                "submit_label": "Submit",
                "note": "We typically reply within 1 business day."
            },
            "live_support": {"title": "Live Support"},
            "assistant": {"title": "Arohio Assistant"},
            "office": {"title": "Visit Arohio in Bihar"}
        }
        _atomic_save(data)

def _load() -> Dict[str, Any]:
    _init_if_missing()
    with open(CONTACT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/", status_code=status.HTTP_200_OK)
def get_contact():
    """Fetch the contact page configuration JSON."""
    return _load()


@router.put("/", status_code=status.HTTP_200_OK)
def put_contact(payload: Dict[str, Any] = Body(...)):
    """Update the contact page configuration JSON."""
    data = payload
    if "meta" not in data:
        data["meta"] = {}
    data["meta"]["updated_at"] = _now_iso()
    _backup()
    _atomic_save(data)
    return data
