# syntax=docker/dockerfile:1
#
# HIVE DOCS (PS5): one image holding the built SPA and the FastAPI backend (docs/05 §7.1).
# Build:  docker build -t hive-docs:local .
# The image contains no .env file, no test data and no secrets: .dockerignore is an allowlist.

# ---- Stage 1: frontend build ------------------------------------------------------------
# Node.js 22 LTS (satisfies Vite 8 engines ^20.19.0 || >=22.12.0; V-02), pinned by digest.
FROM node:22-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: runtime -------------------------------------------------------------------
# Python 3.12 on Debian slim, pinned by digest.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/backend/.venv/bin:${PATH}"

# WeasyPrint 70 system libraries for Debian, as listed in its installation guide
# ("Debian ≥ 11", installing from wheels): Pango, PangoFT2 and the HarfBuzz subsetter.
# Ghostscript is deliberately not installed (docs/05 §7.1, docs/12 §9).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Locked dependencies only (uv.lock), without development tools. uv and its download cache
# are not kept in the image.
COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install --no-cache-dir uv==0.11.32 \
    && uv sync --frozen --no-dev --no-install-project --no-cache \
    && pip uninstall -y uv

COPY backend/app ./app
COPY --from=frontend-build /build/frontend/dist ./app/static

# Run as an unprivileged user that cannot modify the application files.
RUN useradd --system --uid 10001 --no-create-home --home-dir /nonexistent \
        --shell /usr/sbin/nologin hivedocs
# fontconfig (used by WeasyPrint) needs a writable cache directory and the runtime user has
# no home: its cache goes to /tmp (a per-container cache only, never documents or data).
ENV XDG_CACHE_HOME=/tmp/.cache
USER 10001

EXPOSE 8000
# One worker process: the in-memory rate limiter and the render pool assume a single
# process (docs/05 §1). X-Forwarded-* headers are not trusted (docs/12 §2.2).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
