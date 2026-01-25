from crewai.tools import tool
from typing import Optional

# Lazy singleton holders
_memory: Optional["SemanticMemory"] = None
_retriever = None
_retriever_initialized = False


def get_memory():
    """Lazy initialization for SemanticMemory."""
    global _memory
    if _memory is None:
        from app.core.memory.semantic_memory import SemanticMemory
        _memory = SemanticMemory()
    return _memory


def get_rag_retriever():
    """Lazy initialization for RAG retriever."""
    global _retriever, _retriever_initialized
    if not _retriever_initialized:
        try:
            from app.core.rag.retriever import get_retriever
            _retriever = get_retriever()
        except Exception as e:
            print(f"Warning: RAG Retriever init failed: {e}")
            _retriever = None
        _retriever_initialized = True
    return _retriever


# --- CrewAI Tool Definitions ---

@tool("Retrieve Guidelines")
def retrieve_guidelines(query: str) -> str:
    """
    Search medical guidelines (WHO/Ministry of Health) for information on hypertension, diabetes, and lifestyle.
    Useful for checking risk factors, recommended habits, and red flags.
    """
    retriever = get_rag_retriever()
    if not retriever:
        return "RAG Unavailable (Init Failed)"

    try:
        results = retriever.search_guidelines(query, k=3)
        if not results:
            return "No relevant guidelines found."

        formatted = "\n".join([f"- {r['content']} (Score: {r['relevance_score']:.2f})" for r in results])
        return f"Guideline Results:\n{formatted}"
    except Exception as e:
        return f"RAG Error: {e}"


@tool("Recall User Memory")
def recall_memory(user_id: str, query: str) -> str:
    """
    Search past conversations and constraints for this user.
    Args:
        user_id: ID of the user
        query: What to search for
    """
    memory = get_memory()
    results = memory.recall_memories(user_id, query)
    if not results:
        return "No specific memories found."
    return "\n".join([f"- {m['text']}" for m in results])


@tool("Save User Constraint")
def save_constraint(user_id: str, constraint: str) -> str:
    """
    Save a permanent constraint about the user.
    Args:
        user_id: ID of the user
        constraint: The constraint to save
    """
    memory = get_memory()
    memory.store_memory(user_id, constraint, metadata={"type": "constraint"})
    return "Constraint saved."
