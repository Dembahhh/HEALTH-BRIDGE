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


def main():
    print("=" * 60)
    print("  HEALTH-BRIDGE RAG Setup")
    print("  Indexing medical guidelines into ChromaDB")
    print("=" * 60)

    print("\n      Loading embedding model...", flush=True)
    indexer = GuidelineIndexer()
    print("      Model loaded.")

    # Clear existing data
    print("\n[1/3] Clearing existing index...")
    indexer.clear()
    print("      Done.")

    # Index sample guidelines one-by-one with progress
    print(f"\n[2/3] Indexing {len(SAMPLE_GUIDELINES)} sample guidelines...")
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

    stats = {
        "total_documents": len(SAMPLE_GUIDELINES),
        "total_chunks": total_chunks,
        "per_document": stats_per_doc,
    }
    print(f"      Indexed {stats['total_documents']} documents")
    print(f"      Created {stats['total_chunks']} chunks")

    # Show breakdown
    print("\n[3/3] Document breakdown:")
    for name, count in stats["per_document"].items():
        print(f"      - {name}: {count} chunks")

    # Verify
    print("\n" + "-" * 60)
    collection_stats = indexer.get_stats()
    print(f"  Collection: {collection_stats['name']}")
    print(f"  Total indexed: {collection_stats['count']} chunks")
    print("-" * 60)

    print("\n[SUCCESS] RAG setup complete!")
    print("          Guidelines are ready for retrieval.\n")


if __name__ == "__main__":
    main()
