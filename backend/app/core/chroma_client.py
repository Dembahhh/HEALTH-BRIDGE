"""
Shared ChromaDB client factory.

Provides a single ChromaDB client instance based on CHROMA_MODE:
- "persistent" (default): PersistentClient with SQLite (single worker only)
- "http": HttpClient connecting to a ChromaDB server (multi-worker safe)

Usage:
    from app.core.chroma_client import get_chroma_client
    client = get_chroma_client()
"""

import logging
import os

from app.config.settings import settings

logger = logging.getLogger(__name__)

_client = None


def get_chroma_client():
    """Get or create the shared ChromaDB client singleton.

    Returns PersistentClient or HttpClient depending on CHROMA_MODE setting.
    """
    global _client
    if _client is not None:
        return _client

    import chromadb
    from chromadb.config import Settings as ChromaSettings

    mode = settings.CHROMA_MODE.lower()

    if mode == "http":
        logger.info(
            "ChromaDB HTTP mode: connecting to %s:%d",
            settings.CHROMA_HOST,
            settings.CHROMA_PORT,
        )
        chroma_settings_dict = {"anonymized_telemetry": False}
        if settings.CHROMA_AUTH_TOKEN:
            chroma_settings_dict["chroma_client_auth_provider"] = (
                "chromadb.auth.token_authn.TokenAuthClientProvider"
            )
            chroma_settings_dict["chroma_client_auth_credentials"] = settings.CHROMA_AUTH_TOKEN
        _client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(**chroma_settings_dict),
        )
    else:
        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)
        logger.info("ChromaDB persistent mode: %s", persist_dir)
        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    return _client
