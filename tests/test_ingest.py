import hashlib
import pathlib

import pytest
from PIL import Image

from flyercheck.ingest import load


def test_load_designer_pdf(sample_pdf, tmp_path):
    out = tmp_path / "run" / "pages"
    doc, pages = load(str(sample_pdf), str(out))
    sha = hashlib.sha256(sample_pdf.read_bytes()).hexdigest()
    assert (doc.id, doc.sha256, doc.filename, doc.page_count) == (sha[:12], sha, "Designer.pdf", 1)
    assert (doc.campaign_year, doc.campaign_year_source) == (2026, "pdf_metadata")
    assert len(pages) == 1
    p = pages[0]
    assert (p.number, p.width_px, p.height_px) == (1, 1024, 1536)
    assert pathlib.Path(p.path) == out / "page-1.png"
    with Image.open(p.path) as img:
        assert (img.format, img.mode, img.size) == ("PNG", "RGB", (1024, 1536))


def test_load_cli_year_overrides_metadata(sample_pdf, tmp_path):
    doc, _ = load(str(sample_pdf), str(tmp_path), campaign_year=2025)
    assert (doc.campaign_year, doc.campaign_year_source) == (2025, "cli")


def test_load_image_input(tmp_path):
    src = tmp_path / "flyer.jpg"
    Image.new("RGB", (40, 60), "white").save(src)
    doc, pages = load(str(src), str(tmp_path / "out"))
    assert doc.page_count == 1 and doc.campaign_year is None and doc.campaign_year_source is None
    assert (pages[0].width_px, pages[0].height_px) == (40, 60)
    with Image.open(pages[0].path) as img:
        assert img.format == "PNG"


def test_load_rejects_other_types(tmp_path):
    src = tmp_path / "flyer.txt"
    src.write_text("nope")
    with pytest.raises(ValueError):
        load(str(src), str(tmp_path / "out"))
