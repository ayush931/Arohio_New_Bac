# app/api/v1/endpoints/uploads.py
import os
import re
import glob
import uuid
import json
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, status, Form, Request
from fastapi.responses import JSONResponse, Response
from app.services.extractor import extract_pdf_images

router = APIRouter(prefix="/uploads", tags=["uploads"])

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PROJECT_ROOT = os.path.normpath(os.path.join(APP_DIR, ".."))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
UPLOAD_DIR  = os.path.join(STORAGE_DIR, "uploads")
OUTPUT_DIR  = os.path.join(STORAGE_DIR, "output")
PUBLIC_DIR  = os.path.join(PROJECT_ROOT, "public")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)

JOBS = {}

# ---------- small helpers ----------
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.\-]+")
def _safe_name(s: str) -> str:
    """Prevent path traversal / weird chars in pdf_stem & user_id."""
    s = (s or "").strip()
    s = s.replace("..", "")
    s = SAFE_NAME_RE.sub("_", s)
    return s[:200] or "file"

# ========== Existing endpoints ==========

@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    fname = (file.filename or "").lower()
    if not (fname.endswith(".pdf") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    upload_id = str(uuid.uuid4())
    dest_path = os.path.join(UPLOAD_DIR, f"{upload_id}.pdf")

    try:
        with open(dest_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e!r}")

    JOBS[upload_id] = {"status": "uploaded"}
    return JSONResponse({"id": upload_id, "original_filename": file.filename, "status": "uploaded"})

@router.post("/{upload_id}/process")
async def process_pdf(upload_id: str, background_tasks: BackgroundTasks):
    pdf_path = os.path.join(UPLOAD_DIR, f"{upload_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Uploaded PDF not found")

    JOBS[upload_id] = {"status": "processing"}

    def _task():
        try:
            extract_pdf_images(pdf_path, OUTPUT_DIR, job_id=upload_id)
            JOBS[upload_id] = {"status": "done"}
        except Exception as e:
            JOBS[upload_id] = {"status": "error", "error": str(e)}

    background_tasks.add_task(_task)
    return {"id": upload_id, "status": "processing"}

@router.get("/{upload_id}/status")
async def get_status(upload_id: str):
    job = JOBS.get(upload_id)
    if job:
        return {"id": upload_id, **job}

    manifest_path = os.path.join(OUTPUT_DIR, upload_id, "manifest.json")
    pdf_path = os.path.join(UPLOAD_DIR, f"{upload_id}.pdf")
    if os.path.exists(manifest_path):
        return {"id": upload_id, "status": "done"}
    if os.path.exists(pdf_path):
        return {"id": upload_id, "status": "uploaded"}
    return {"id": upload_id, "status": "unknown"}

@router.get("/{upload_id}/manifest")
async def get_manifest(upload_id: str):
    manifest_path = os.path.join(OUTPUT_DIR, upload_id, "manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="Manifest not ready")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ========== Save manifest into public/OngoingJson/<user_id>/ ==========

@router.post("/save-json", status_code=status.HTTP_201_CREATED)
async def save_ongoing_json_file(
    request: Request,
    json_file: UploadFile = File(...),
    user_id: str = Form(...),
    pdf_stem: str = Form(...),
    result_url: str = Form("")
):
    user_id  = _safe_name(user_id)
    pdf_stem = _safe_name(pdf_stem)

    if not user_id or not pdf_stem:
        raise HTTPException(status_code=400, detail="user_id and pdf_stem are required")

    base_dir = os.path.join(PUBLIC_DIR, "OngoingJson", user_id)
    os.makedirs(base_dir, exist_ok=True)

    # write manifest
    manifest_name = f"{pdf_stem}.json"
    manifest_path = os.path.join(base_dir, manifest_name)
    data_bytes = await json_file.read()
    try:
        with open(manifest_path, "wb") as f:
            f.write(data_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write manifest: {e!r}")

    # write sidecar with result_url
    sidecar_name = f"{pdf_stem}__result_url.json"
    sidecar_path = os.path.join(base_dir, sidecar_name)
    try:
        with open(sidecar_path, "w", encoding="utf-8") as f:
            json.dump({"result_url": result_url or ""}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write result_url file: {e!r}")

    origin = str(request.base_url).rstrip("/")
    return {
        "ok": True,
        "saved": {
            "manifest": f"{origin}/OngoingJson/{user_id}/{manifest_name}",
            "result_url_json": f"{origin}/OngoingJson/{user_id}/{sidecar_name}",
        }
    }

# ========== NEW: Read-back APIs so frontend can show JSON ==========

BASE_ONGOING = os.path.join(PUBLIC_DIR, "OngoingJson")

@router.get("/json/{user_id}")
def list_saved_json(user_id: str):
    """List all saved JSON files for a given user."""
    user_id = _safe_name(user_id)
    user_dir = os.path.join(BASE_ONGOING, user_id)
    if not os.path.isdir(user_dir):
        return {"files": []}

    files = []
    for fp in glob.glob(os.path.join(user_dir, "*.json")):
        name = os.path.basename(fp)
        stem = name[:-5] if name.endswith(".json") else name
        files.append({
            "pdf_stem": stem,
            # API path to fetch the JSON content directly
            "api_url": f"/api/v1/uploads/json/{user_id}/{stem}",
            # static file URL (served by StaticFiles if you mounted /public)
            "static_url": f"/OngoingJson/{user_id}/{name}",
        })
    return {"files": files}

@router.get("/json/{user_id}/{pdf_stem}")
def get_saved_json(user_id: str, pdf_stem: str):
    """Return the saved manifest JSON for user + pdf_stem (or its sidecar)."""
    user_id  = _safe_name(user_id)
    pdf_stem = _safe_name(pdf_stem)

    manifest_path = os.path.join(BASE_ONGOING, user_id, f"{pdf_stem}.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "rb") as f:
            return Response(content=f.read(), media_type="application/json")

    sidecar_path = os.path.join(BASE_ONGOING, user_id, f"{pdf_stem}__result_url.json")
    if os.path.exists(sidecar_path):
        with open(sidecar_path, "rb") as f:
            return Response(content=f.read(), media_type="application/json")

    raise HTTPException(status_code=404, detail="Saved JSON not found")
