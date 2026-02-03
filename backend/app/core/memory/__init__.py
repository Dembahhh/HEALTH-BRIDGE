from .semantic_memory import SemanticMemory

# Phase 2: Cognee Memory (optional, with fallback)
try:
    from app.core.memory.cognee_memory import (
        CogneeMemoryManager,
        get_cognee_memory,
        run_async,
        MemoryNode,
        MemorySearchResult
    )
    COGNEE_AVAILABLE = True
except ImportError:
    COGNEE_AVAILABLE = False
    CogneeMemoryManager = None
    get_cognee_memory = None
    run_async = None
    MemoryNode = None
    MemorySearchResult = None

# Memory Factory (always available)
try:
    from app.core.memory.memory_factory import (
        get_memory,
        get_memory_adapter,
        get_memory_backend,
        MemoryAdapter,
        BACKEND_SEMANTIC,
        BACKEND_COGNEE
    )
except ImportError:
    # Fallback if factory not created yet
    def get_memory():
        return SemanticMemory()
    
    def get_memory_adapter():
        return None
    
    def get_memory_backend():
        return "semantic"
    
    MemoryAdapter = None
    BACKEND_SEMANTIC = "semantic"
    BACKEND_COGNEE = "cognee"


__all__ = [
    # Phase 1
    "SemanticMemory",
    
    # Phase 2
    "CogneeMemoryManager",
    "get_cognee_memory",
    "run_async",
    "MemoryNode",
    "MemorySearchResult",
    "COGNEE_AVAILABLE",
    
    # Factory
    "get_memory",
    "get_memory_adapter",
    "get_memory_backend",
    "MemoryAdapter",
    "BACKEND_SEMANTIC",
    "BACKEND_COGNEE",
]