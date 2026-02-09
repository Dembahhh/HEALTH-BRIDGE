# ============================================================
# HEALTH-BRIDGE Backend — Optimized Multi-stage Docker Build
# ============================================================
# Stage 1: Install Python deps into a virtualenv (cached layer)
# Stage 2: Slim runtime with only the venv + app code
# ============================================================

# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# System deps for building native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Use a virtualenv so we can COPY just /opt/venv instead of all site-packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# BuildKit cache mount keeps pip's download cache across builds.
# --no-compile skips .pyc generation (saves ~15% layer size).
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-compile --timeout=120 -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy ONLY the virtualenv — not all of /usr/local
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Create persistent data directory for ChromaDB
RUN mkdir -p /app/data/chroma

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8000/health',timeout=5); assert r.status_code==200"

# Single worker: CrewAI uses its own ThreadPoolExecutor internally
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
