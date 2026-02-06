"""
ChromaDB Configuration Module

Centralizes all ChromaDB configuration settings to avoid duplication
and make maintenance easier.
"""
import os

# Authentication provider class path for ChromaDB HTTP client
# This is the full module path for token-based authentication
CHROMA_AUTH_PROVIDER_CLASS = "chromadb.auth.token_authn.TokenAuthClientProvider"

# Environment variables for ChromaDB configuration
CHROMA_MODE = os.getenv("CHROMA_MODE", "persistent")  # "persistent" or "http"

# Persistent mode settings (for development and single-worker deployments)
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_memory")  # For semantic memory
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")  # For RAG retriever

# HTTP mode settings (for production multi-worker deployments)
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_AUTH_TOKEN = os.getenv("CHROMA_AUTH_TOKEN")  # Optional but recommended for production
