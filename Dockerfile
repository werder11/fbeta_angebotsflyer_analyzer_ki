# syntax=docker/dockerfile:1
# FlyerCheck container (ADR-0007): one image for the API (Cloud Run service) and batch jobs (Cloud Run Jobs).

# ---- builder: resolve and install locked dependencies with uv ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---- runtime: slim Python, non-root ----
FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN groupadd --system --gid 10001 flyercheck \
 && useradd --system --uid 10001 --gid flyercheck --home-dir /app --no-create-home flyercheck

WORKDIR /app

COPY --from=builder --chown=flyercheck:flyercheck /app/.venv /app/.venv
# Replay recordings, golden labels and the sample flyer: offline runs and smoke tests inside the image.
COPY --chown=flyercheck:flyercheck data/recordings ./data/recordings
COPY --chown=flyercheck:flyercheck data/golden ./data/golden
COPY --chown=flyercheck:flyercheck data/samples ./data/samples

RUN mkdir -p /app/out && chown flyercheck:flyercheck /app/out
USER flyercheck

EXPOSE 8080

# Shell form so Cloud Run's $PORT is honoured; exec keeps uvicorn as PID 1 for clean SIGTERM handling.
# Batch use: `docker run flyercheck flyercheck run data/samples/Designer.pdf --mode replay`.
CMD ["sh", "-c", "exec flyercheck serve --host 0.0.0.0 --port \"${PORT:-8080}\""]
