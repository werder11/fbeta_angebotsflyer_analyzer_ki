"""Ingest: validate, hash, extract page images. Owned by track T2."""
from __future__ import annotations

import hashlib
import io
import pathlib
import re

import pymupdf
from PIL import Image

from flyercheck.domain.models import Document, PageImage

RENDER_DPI = 200
FULL_PAGE_COVERAGE = 0.9
_IMAGE_EXT = {".png", ".jpg", ".jpeg"}


def _save_png(img: Image.Image, path: pathlib.Path) -> tuple[int, int]:
    img.convert("RGB").save(path, format="PNG")
    return img.width, img.height


def _full_page_raster(doc: pymupdf.Document, page: pymupdf.Page) -> Image.Image | None:
    """The page's single embedded image if its placement covers >= 90 % of the page, else None."""
    infos = page.get_image_info(xrefs=True)
    if len(infos) != 1 or not infos[0].get("xref"):
        return None
    page_area = page.rect.width * page.rect.height
    placed = pymupdf.Rect(infos[0]["bbox"]) & page.rect
    if page_area <= 0 or placed.is_empty or placed.width * placed.height < FULL_PAGE_COVERAGE * page_area:
        return None
    pix = pymupdf.Pixmap(doc, infos[0]["xref"])
    if pix.alpha or pix.colorspace is None or pix.colorspace.n not in (1, 3):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def _year_from_metadata(doc: pymupdf.Document) -> int | None:
    m = re.match(r"(?:D:)?(\d{4})", (doc.metadata or {}).get("creationDate") or "")
    return int(m.group(1)) if m else None


def load(path: str, out_dir: str, campaign_year: int | None = None) -> tuple[Document, list[PageImage]]:
    src = pathlib.Path(path)
    ext = src.suffix.lower()
    if ext != ".pdf" and ext not in _IMAGE_EXT:
        raise ValueError(f"unsupported file type {ext!r}: expected .pdf, .png or .jpg")
    data = src.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pages: list[PageImage] = []
    meta_year: int | None = None
    if ext == ".pdf":
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            meta_year = _year_from_metadata(doc)
            for i, page in enumerate(doc, 1):
                target = out / f"page-{i}.png"
                img = _full_page_raster(doc, page)
                if img is not None:
                    w, h = _save_png(img, target)
                else:
                    pix = page.get_pixmap(dpi=RENDER_DPI, alpha=False)
                    pix.save(str(target))
                    w, h = pix.width, pix.height
                pages.append(PageImage(number=i, width_px=w, height_px=h, path=str(target)))
    else:
        target = out / "page-1.png"
        with Image.open(io.BytesIO(data)) as img:
            w, h = _save_png(img, target)
        pages.append(PageImage(number=1, width_px=w, height_px=h, path=str(target)))

    if campaign_year is not None:
        year, source = campaign_year, "cli"
    elif meta_year is not None:
        year, source = meta_year, "pdf_metadata"
    else:
        year, source = None, None
    document = Document(id=sha[:12], sha256=sha, filename=src.name, page_count=len(pages),
                        campaign_year=year, campaign_year_source=source)
    return document, pages
