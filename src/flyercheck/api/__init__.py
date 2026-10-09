"""REST API + review decisions (docs/api/README.md). Owned by Phase 3 track E3."""
from fastapi import FastAPI


def create_app(out_dir: str = "out", recordings_dir: str = "data/recordings") -> FastAPI:
    raise NotImplementedError
