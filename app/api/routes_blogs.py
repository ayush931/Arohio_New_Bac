# app/api/v1/routes_blogs.py
from fastapi import APIRouter, Body, HTTPException, Query, status
from typing import Any, Dict, List, Optional
import os, json, re, time, tempfile, shutil
from datetime import datetime, timezone

router = APIRouter(prefix="/blogs", tags=["blogs"])

# ---- JSON location ----
DATA_DIR = os.path.join("storage", "content")
BLOGS_JSON = os.path.join(DATA_DIR, "blogs.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# ---- helpers ----
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)        # remove non-word
    s = re.sub(r"[\s_-]+", "-", s)        # collapse
    s = re.sub(r"^-+|-+$", "", s)         # trim -
    return s or f"post-{int(time.time())}"

def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def _init_if_missing():
    _ensure_dirs()
    if not os.path.exists(BLOGS_JSON):
        data = {
            "meta": {"version": 1, "generated_at": _now_iso()},
            "posts": []
        }
        _atomic_save(data)

def _load() -> Dict[str, Any]:
    _init_if_missing()
    with open(BLOGS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def _backup():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(BLOGS_JSON, os.path.join(BACKUP_DIR, f"blogs-{ts}.json"))

def _atomic_save(data: Dict[str, Any]):
    data["meta"] = data.get("meta", {})
    data["meta"]["generated_at"] = _now_iso()
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="blogs-", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, BLOGS_JSON)  # atomic on same filesystem
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

def _next_id(posts: List[Dict[str, Any]]) -> int:
    return (max((p.get("id", 0) for p in posts), default=0) + 1) or 1

def _find_by_id(posts: List[Dict[str, Any]], blog_id: int) -> Optional[Dict[str, Any]]:
    return next((p for p in posts if p.get("id") == blog_id), None)

def _find_by_slug(posts: List[Dict[str, Any]], slug: str) -> Optional[Dict[str, Any]]:
    return next((p for p in posts if p.get("slug") == slug), None)

def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    # tags can be comma string or list -> always list[str]
    tags = payload.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        tags = [str(t).strip() for t in tags if str(t).strip()]
    else:
        tags = []
    payload["tags"] = tags

    # author object
    author = payload.get("author") or {}
    payload["author"] = {
        "name": author.get("name") or "",
        "avatar": author.get("avatar") or ""
    }

    # booleans / defaults
    payload["featured"] = bool(payload.get("featured", False))
    payload["status"] = payload.get("status") or "published"  # draft | published | archived
    payload["content"] = payload.get("content") or {"format": "markdown", "body": ""}

    # date (keep as YYYY-MM-DD string like your UI)
    if payload.get("date"):
        payload["date"] = str(payload["date"])

    # readMin coercion
    if "readMin" in payload and payload["readMin"] is not None:
        try: payload["readMin"] = int(payload["readMin"])
        except: payload["readMin"] = None

    return payload

def _validate_required(payload: Dict[str, Any]):
    if not payload.get("title"):
        raise HTTPException(status_code=400, detail="Title is required")
    # if publishing, ensure minimum fields
    if payload.get("status", "published") == "published":
        if not payload.get("excerpt"):
            raise HTTPException(status_code=400, detail="Excerpt required for published post")
        if not payload.get("image"):
            raise HTTPException(status_code=400, detail="Image URL required for published post")
        if not payload.get("content", {}).get("body"):
            raise HTTPException(status_code=400, detail="Content body required for published post")

# ---- ROUTES ----

@router.get("/")
def list_blogs(
    status_filter: Optional[str] = Query(None, description="draft|published|archived"),
    include_unpublished: bool = Query(False, description="Admin view: include all statuses"),
    q: Optional[str] = Query(None, description="Search in title/excerpt/tags"),
):
    """
    Public: by default returns only published posts.
    Admin: pass include_unpublished=true to get everything (or filter by status).
    """
    print("[GET] /blogs called", {"status_filter": status_filter, "include_unpublished": include_unpublished, "q": q})
    data = _load()
    posts = data.get("posts", [])

    if not include_unpublished and not status_filter:
        posts = [p for p in posts if p.get("status") == "published"]

    if status_filter:
        posts = [p for p in posts if p.get("status") == status_filter]

    if q:
        needle = q.strip().lower()
        def match(p):
            in_title = needle in (p.get("title","").lower())
            in_excerpt = needle in (p.get("excerpt","").lower())
            in_tags = needle in " ".join(p.get("tags", [])).lower()
            return in_title or in_excerpt or in_tags
        posts = [p for p in posts if match(p)]

    # latest first based on 'date' string desc (like your UI)
    posts.sort(key=lambda p: p.get("date",""), reverse=True)
    print(f"[GET] returning {len(posts)} posts")
    return {"meta": data.get("meta", {}), "posts": posts}


@router.get("/{id_or_slug}")
def get_blog(id_or_slug: str):
    """
    Fetch by numeric id OR slug.
    Public: returns only published.
    Admin: pass ?include_unpublished=true
    """
    print("[GET] /blogs/", id_or_slug)
    data = _load()
    posts = data.get("posts", [])
    row = None
    if id_or_slug.isdigit():
        row = _find_by_id(posts, int(id_or_slug))
    if not row:
        row = _find_by_slug(posts, id_or_slug)

    if not row:
        raise HTTPException(404, detail="Blog not found")

    # If not published and no admin flag, hide
    # (Simple approach: require include_unpublished=true query for drafts)
    # You can add auth later.
    return row


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_blog(payload: Dict[str, Any] = Body(...)):
    """
    Create new blog post in blogs.json
    """
    print("[POST] /blogs payload =", payload)
    payload = _normalize_payload(payload)
    _validate_required(payload)

    data = _load()
    posts = data.get("posts", [])

    # slug
    slug = payload.get("slug") or _slugify(payload["title"])
    # ensure unique
    base = slug
    i = 2
    while _find_by_slug(posts, slug):
        slug = f"{base}-{i}"
        i += 1

    row = {
        "id": _next_id(posts),
        "slug": slug,
        "title": payload["title"],
        "excerpt": payload.get("excerpt", ""),
        "category": payload.get("category"),
        "tags": payload.get("tags", []),
        "date": payload.get("date"),          # "YYYY-MM-DD"
        "readMin": payload.get("readMin"),
        "author": payload.get("author", {"name":"", "avatar":""}),
        "image": payload.get("image"),
        "featured": payload.get("featured", False),
        "status": payload.get("status", "published"),
        "seo": payload.get("seo", {}),
        "content": payload.get("content", {"format":"markdown", "body":""}),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "published_at": _now_iso() if payload.get("status","published")=="published" else None,
    }

    posts.append(row)
    data["posts"] = posts
    _backup()
    _atomic_save(data)
    print("[POST] created blog id =", row["id"], "slug =", row["slug"])
    return row


@router.put("/{blog_id}")
def update_blog(blog_id: int, payload: Dict[str, Any] = Body(...)):
    print("[PUT] /blogs/", blog_id, "payload =", payload)
    payload = _normalize_payload(payload)
    data = _load()
    posts = data.get("posts", [])
    row = _find_by_id(posts, blog_id)
    if not row:
        raise HTTPException(404, detail="Blog not found")

    # update basic fields
    for field in [
        "title","excerpt","category","tags","date","readMin",
        "author","image","featured","status","seo","content"
    ]:
        if field in payload and payload[field] is not None:
            row[field] = payload[field]

    # optionally allow slug change (if explicitly sent)
    if "slug" in payload and payload["slug"]:
        new_slug = _slugify(payload["slug"])
        if new_slug != row["slug"]:
            if _find_by_slug(posts, new_slug):
                raise HTTPException(400, detail="Slug already exists")
            row["slug"] = new_slug

    row["updated_at"] = _now_iso()
    if row.get("status") == "published" and not row.get("published_at"):
        row["published_at"] = _now_iso()

    _backup()
    _atomic_save(data)
    print("[PUT] updated blog id =", blog_id)
    return row


@router.delete("/{blog_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blog(blog_id: int):
    print("[DELETE] /blogs/", blog_id)
    data = _load()
    posts = data.get("posts", [])
    row = _find_by_id(posts, blog_id)
    if not row:
        raise HTTPException(404, detail="Blog not found")
    posts = [p for p in posts if p.get("id") != blog_id]
    data["posts"] = posts
    _backup()
    _atomic_save(data)
    print("[DELETE] deleted blog id =", blog_id)
    return None


@router.put("/reorder/featured")
def set_featured(blog_id: int = Body(..., embed=True), featured: bool = Body(True, embed=True)):
    """
    Toggle 'featured' flag for a blog (admin convenience).
    """
    print("[PUT] /blogs/reorder/featured", {"blog_id": blog_id, "featured": featured})
    data = _load()
    posts = data.get("posts", [])
    row = _find_by_id(posts, blog_id)
    if not row:
        raise HTTPException(404, detail="Blog not found")
    row["featured"] = bool(featured)
    row["updated_at"] = _now_iso()
    _backup()
    _atomic_save(data)
    return row
