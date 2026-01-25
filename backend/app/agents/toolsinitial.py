from crewai.tools import tool
from app.core.memory.semantic_memory import SemanticMemory
from app.core.rag.retriever import get_retriever

# Instantiate singletons for tools
memory = SemanticMemory()
try:
    retriever = get_retriever()
except Exception as e:
    print(f"Warning: RAG Retriever init failed: {e}")
    retriever = None

# --- CrewAI Tool Definitions ---

@tool("Retrieve Guidelines")
def retrieve_guidelines(query: str) -> str:
    """
    Search medical guidelines (WHO/Ministry of Health) for information on hypertension, diabetes, and lifestyle.
    Useful for checking risk factors, recommended habits, and red flags.
    """
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
    memory.store_memory(user_id, constraint, metadata={"type": "constraint"})
    return "Constraint saved."
