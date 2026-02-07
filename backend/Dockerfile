FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies for building native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch FIRST (saves ~1.8GB vs full CUDA torch)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories for ChromaDB persistent storage
RUN mkdir -p /app/data/chroma /app/data/chroma_memory

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
