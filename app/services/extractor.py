# app/services/extractor.py
import os, io, re, json, pathlib
from typing import Dict, Any, List, Tuple, Optional

import fitz  # PyMuPDF
from PIL import Image

try:
    import pandas as pd  # optional (for Excel)
except Exception:
    pd = None

FIGURE_REGEX = re.compile(r'^\s*(?:Figure|Fig\.?)\s*(\d+)\s*[:.\-]?\s*(.*)$', re.IGNORECASE)

def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _overlap_ratio(a: Tuple[float,float,float,float], b: Tuple[float,float,float,float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    w = max(0, min(ax1, bx1) - max(ax0, bx0))
    h = max(0, min(ay1, by1) - max(ay0, by0))
    inter = w * h
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    if area_a <= 0 or area_b <= 0:
        return 0.0
    return inter / min(area_a, area_b)

def _text_blocks(page) -> List[Dict[str, Any]]:
    """Collect text blocks with approximate bounding boxes to help find captions."""
    raw = page.get_text("rawdict")
    blocks = []
    for b in raw.get("blocks", []):
        if b.get("type") != 0:  # text blocks only
            continue
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        parts = []
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                parts.append(span.get("text", ""))
                sx0, sy0, sx1, sy1 = span.get("bbox")
                x0, y0 = min(x0, sx0), min(y0, sy0)
                x1, y1 = max(x1, sx1), max(y1, sy1)
        txt = " ".join(parts).strip()
        if txt:
            blocks.append({"bbox": (x0, y0, x1, y1), "text": txt})
    return blocks

def _find_caption(img_bbox, text_blocks,
                  below_px=120, above_px=60) -> Tuple[Optional[str], Optional[str]]:
    """
    Heuristic:
    - Prefer text directly BELOW the image (<= below_px).
    - Otherwise look just ABOVE (<= above_px).
    - Require at least 25% horizontal overlap.
    """
    ix0, iy0, ix1, iy1 = img_bbox

    below = [tb for tb in text_blocks
             if tb["bbox"][1] >= iy1
             and tb["bbox"][1] - iy1 <= below_px
             and _overlap_ratio(img_bbox, tb["bbox"]) >= 0.25]
    below.sort(key=lambda tb: tb["bbox"][1] - iy1)

    above = [tb for tb in text_blocks
             if iy0 >= tb["bbox"][3]
             and iy0 - tb["bbox"][3] <= above_px
             and _overlap_ratio(img_bbox, tb["bbox"]) >= 0.25]
    above.sort(key=lambda tb: iy0 - tb["bbox"][3])

    chosen = below[0] if below else (above[0] if above else None)
    if not chosen:
        return None, None

    text = chosen["text"].strip()
    m = FIGURE_REGEX.match(text)
    if m:
        fig_number = f"Figure {m.group(1)}"
        caption = m.group(2).strip() or text
        return fig_number, caption
    return None, text

def extract_pdf_images(pdf_path: str, out_root: str, job_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract every image from a PDF and write:
      storage/output/<job_id>/images/*.png
      storage/output/<job_id>/manifest.json
      (optional) storage/output/<job_id>/manifest.xlsx
    Returns the manifest dict.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pdf_stem = job_id or pathlib.Path(pdf_path).stem
    out_dir = os.path.join(out_root, pdf_stem)
    img_dir = os.path.join(out_dir, "images")
    _ensure_dir(img_dir)

    doc = fitz.open(pdf_path)
    manifest: Dict[str, Any] = {
        "pdf_file": pdf_path,
        "output_dir": out_dir,
        "images": []
    }

    for i in range(len(doc)):
        page = doc.load_page(i)
        page_no = i + 1
        text_blocks = _text_blocks(page)
        raw = page.get_text("rawdict")
        img_blocks = [b for b in raw.get("blocks", []) if b.get("type") == 1]

        count = 0
        for b in img_blocks:
            bbox = tuple(b.get("bbox", []))
            xref = b.get("image")
            if not xref:
                continue

            try:
                base = doc.extract_image(xref)
            except Exception:
                base = None
                for im in page.get_images(full=True):
                    if im[0] == xref:
                        base = doc.extract_image(xref)
                        break
            if not base:
                continue

            img_bytes = base.get("image")
            ext = base.get("ext", "png")
            count += 1
            img_id = f"page-{page_no}-img-{count}"
            file_name = f"{img_id}.{ext}"
            file_path = os.path.join(img_dir, file_name)

            # Write the image (normalize via PIL if needed)
            width = base.get("width")
            height = base.get("height")
            try:
                with Image.open(io.BytesIO(img_bytes)) as im:
                    im.save(file_path)
                    width, height = im.width, im.height
            except Exception:
                with open(file_path, "wb") as f:
                    f.write(img_bytes)

            fig_num, caption = _find_caption(bbox, text_blocks)

            manifest["images"].append({
                "id": img_id,
                "page": page_no,
                "bbox": [round(x, 2) for x in bbox],
                "image_path": file_path,
                "figure_number": fig_num,
                "caption_text": caption,
                "width": width,
                "height": height
            })

    # Write JSON manifest
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Optional: Excel
    if pd:
        rows = [{
            "id": it["id"],
            "page": it["page"],
            "image_path": it["image_path"],
            "figure_number": it["figure_number"],
            "caption_text": it["caption_text"],
            "width": it["width"],
            "height": it["height"],
            "bbox": str(it["bbox"]),
        } for it in manifest["images"]]
        df = pd.DataFrame(rows)
        df.to_excel(os.path.join(out_dir, "manifest.xlsx"), index=False)

    return manifest
