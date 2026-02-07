# ──────────────── Stage 1: Dependencies ────────────────
# This stage installs all Python packages. It only rebuilds when
# requirements.txt changes, so code-only edits skip this layer entirely.
FROM python:3.11-slim AS deps

WORKDIR /app

# System dependencies for building native extensions (grpcio, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch FIRST — saves ~1.6GB vs full CUDA torch.
# torchvision is NOT installed (unused in this project).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ──────────────── Stage 2: Runtime (slim) ────────────────
# Copy only installed packages from deps stage — no build-essential,
# no pip cache, no intermediate build artifacts.
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed Python packages and CLI scripts from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code (changes frequently — last layer for fast rebuilds)
COPY . .

# Create data directories for ChromaDB persistent storage
RUN mkdir -p /app/data/chroma /app/data/chroma_memory

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
