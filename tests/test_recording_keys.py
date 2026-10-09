"""Recording keys must not depend on PNG encoding (zlib differs between macOS dev and Linux CI)."""
import io

from PIL import Image

from flyercheck.llm.port import request_key


def _png(img: Image.Image, level: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=level)
    return buf.getvalue()


def test_key_independent_of_png_encoding(page_png):
    img = Image.open(io.BytesIO(page_png)).convert("RGB").crop((0, 0, 200, 200))
    fast, small = _png(img, 1), _png(img, 9)
    assert fast != small
    assert request_key("vision", "p", [fast], {}) == request_key("vision", "p", [small], {})


def test_key_changes_with_pixels(page_png):
    img = Image.open(io.BytesIO(page_png)).convert("RGB").crop((0, 0, 200, 200))
    other = img.copy()
    other.putpixel((0, 0), (0, 0, 0) if img.getpixel((0, 0)) != (0, 0, 0) else (255, 255, 255))
    assert request_key("vision", "p", [_png(img, 6)], {}) != request_key("vision", "p", [_png(other, 6)], {})
