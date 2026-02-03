from crewai.tools import tool
from typing import Optional

# Lazy singleton holders
_memory: Optional["SemanticMemory"] = None
_retriever = None
_retriever_initialized = False
_query_rewriter: Optional["QueryRewriter"] = None
_critic: Optional["CorrectiveRAGCritic"] = None


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


def get_query_rewriter():
    """Lazy initialization for QueryRewriter."""
    global _query_rewriter
    if _query_rewriter is None:
        from app.core.rag.query_rewriter import QueryRewriter
        _query_rewriter = QueryRewriter()
    return _query_rewriter


def get_critic():
    """Lazy initialization for CorrectiveRAGCritic."""
    global _critic
    if _critic is None:
        from app.core.rag.critic import CorrectiveRAGCritic
        _critic = CorrectiveRAGCritic(confidence_threshold=0.6)
    return _critic


# --- CrewAI Tool Definitions ---

@tool("Retrieve Guidelines")
def retrieve_guidelines(query: str, condition: Optional[str] = None, topic: Optional[str] = None) -> str:
    """
    Search medical guidelines (WHO/Ministry of Health) for information on hypertension, diabetes, and lifestyle.
    Useful for checking risk factors, recommended habits, and red flags.
    Args:
        query: The search query
        condition: Optional filter for health condition (e.g. 'hypertension', 'diabetes')
        topic: Optional filter for specific topic (e.g. 'diet', 'activity', 'red_flags')
    """
    retriever = get_rag_retriever()
    if not retriever:
        return "RAG Unavailable (Init Failed)"

    try:
        # Step 1: Rewrite query for better retrieval
        rewriter = get_query_rewriter()
        rewrite_result = rewriter.rewrite_query(query)
        enhanced_query = rewrite_result["rewritten_query"]
        auto_filters = rewrite_result["filters"]

        # Use explicitly provided filters if available, otherwise use auto-detected ones
        final_condition = condition or auto_filters.get("condition")
        final_topic = topic or auto_filters.get("topic")

        # Step 2: Search with enhanced query and metadata filters
        results = retriever.search_guidelines(
            enhanced_query,
            condition=final_condition,
            topic=final_topic,
            k=3
        )

        if not results:
            # Fallback: search without filters in case metadata filtering was too strict
            results = retriever.search_guidelines(enhanced_query, k=3)

        if not results:
            return "No relevant guidelines found."

        # Step 3: Corrective RAG - validate retrieval quality
        critic = get_critic()
        combined_content = " ".join([r["content"] for r in results])
        review = critic.review_answer(combined_content, results, query)

        if critic.should_retry(review):
            refinements = review.get("suggested_refinements", [])
            retry_query = f"{enhanced_query} {refinements[0]}" if refinements else enhanced_query
            retry_results = retriever.search_guidelines(retry_query, k=3)
            if retry_results:
                results = retry_results

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
    try:
        memory = get_memory()
        results = memory.recall_memories(user_id, query)
        if not results:
            return "No specific memories found."
        return "\n".join([f"- {m.get('text', 'N/A')}" for m in results])
    except Exception as e:
        return f"Memory recall error: {e}"


@tool("Save User Constraint")
def save_constraint(user_id: str, constraint: str) -> str:
    """
    Save a permanent constraint about the user.
    Args:
        user_id: ID of the user
        constraint: The constraint to save
    """
    try:
        memory = get_memory()
        memory.store_memory(user_id, constraint, metadata={"type": "constraint"})
        return "Constraint saved."
    except Exception as e:
        return f"Failed to save constraint: {e}"


@tool("Save User Memory")
def save_memory(user_id: str, text: str, memory_type: str) -> str:
    """
    Save a memory about the user for future sessions.
    Args:
        user_id: ID of the user
        text: The information to save
        memory_type: Type of memory - one of: profile, constraint, habit_plan, outcome
    """
    valid_types = {"profile", "constraint", "habit_plan", "outcome"}
    if memory_type not in valid_types:
        memory_type = "profile"

    try:
        memory = get_memory()
        memory.store_memory(user_id, text, metadata={"type": memory_type})
        return f"Memory saved (type: {memory_type})."
    except Exception as e:
        return f"Failed to save memory: {e}"
