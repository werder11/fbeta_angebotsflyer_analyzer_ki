"""Ingest: validate, hash, extract page images. Owned by track T2."""
from flyercheck.domain.models import Document, PageImage


def load(path: str, out_dir: str, campaign_year: int | None = None) -> tuple[Document, list[PageImage]]:
    raise NotImplementedError
