"""
RAG Setup Script

Run this script to index guideline documents into ChromaDB.

Usage:
    python setup_rag.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.core.rag.indexer import GuidelineIndexer, SAMPLE_GUIDELINES
from app.config.settings import settings


def main():
    print("=" * 60)
    print("  HEALTH-BRIDGE RAG Setup")
    print("  Indexing medical guidelines into ChromaDB")
    print("=" * 60)

    print("\n      Loading embedding model...", flush=True)
    indexer = GuidelineIndexer()
    print("      Model loaded.")

    # Clear existing data
    print("\n[1/4] Clearing existing index...")
    indexer.clear()
    print("      Done.")

    # ---- Step 2: Embedded sample guidelines ----
    print(f"\n[2/4] Indexing {len(SAMPLE_GUIDELINES)} embedded sample guidelines...")
    total_chunks = 0
    stats_per_doc = {}
    for i, (name, data) in enumerate(SAMPLE_GUIDELINES.items(), 1):
        print(f"      ({i}/{len(SAMPLE_GUIDELINES)}) {name}...", end=" ", flush=True)
        num_chunks = indexer.index_guideline(
            content=data["content"],
            condition=data["condition"],
            topic=data["topic"],
            source=data["source"],
        )
        stats_per_doc[name] = num_chunks
        total_chunks += num_chunks
        print(f"{num_chunks} chunks")

    print(f"      Indexed {len(SAMPLE_GUIDELINES)} documents, {total_chunks} chunks")

    # ---- Step 3: Directory guideline files ----
    guidelines_dir = os.path.join(
        settings.CHROMA_PERSIST_DIR, "..", "guidelines"
    )
    print(f"\n[3/4] Indexing directory: {guidelines_dir}")
    dir_stats = indexer.index_from_directory(guidelines_dir)

    if "error" in dir_stats:
        print(f"      Warning: {dir_stats['error']}")
    else:
        print(f"      Files:  {dir_stats['files_processed']}")
        print(f"      Chunks: {dir_stats['total_chunks']}")
        for fname, info in dir_stats["per_file"].items():
            print(
                f"        - {fname}: {info['chunks']} chunks "
                f"[{info['source']}/{info['condition']}/{info['topic']}]"
            )
        total_chunks += dir_stats["total_chunks"]

    # ---- Step 4: Verify ----
    print(f"\n[4/4] Verification:")
    collection_stats = indexer.get_stats()
    print(f"      Collection:      {collection_stats['name']}")
    print(f"      Total indexed:   {collection_stats['count']} chunks")
    print("-" * 60)

    print("\n[SUCCESS] RAG setup complete!")
    print("          Guidelines are ready for retrieval.\n")


if __name__ == "__main__":
    main()
