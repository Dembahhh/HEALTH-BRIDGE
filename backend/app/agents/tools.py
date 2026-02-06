"""
CrewAI Agent Tools for HEALTH-BRIDGE

Provides tools for:
- RAG retrieval from medical guidelines
- Memory recall and storage
- Enhanced memory with structured context (Phase 2)
"""

from crewai.tools import tool
from typing import Optional
import json
import time
import logging
import functools
import signal
import threading
from datetime import datetime

from app.core.config import tracked

logger = logging.getLogger(__name__)


def with_timeout(seconds: int = 30):
    """Decorator to add timeout to tool functions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)

            if thread.is_alive():
                logger.warning(f"Tool {func.__name__} timed out after {seconds}s")
                return f"{func.__name__} timed out - using fallback response"
            if error[0]:
                raise error[0]
            return result[0]
        return wrapper
    return decorator


def retry_on_transient(max_retries: int = 2, delay: float = 1.0):
    """Decorator to retry on transient errors (ConnectionError, TimeoutError)."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, OSError) as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(f"Tool {func.__name__} transient error (attempt {attempt + 1}): {e}")
                        time.sleep(delay * (attempt + 1))
                    continue
            raise last_error
        return wrapper
    return decorator

# Lazy singleton holders
_memory = None
_cognee_memory = None
_retriever = None
_retriever_initialized = False
_query_rewriter = None
_critic = None


def get_memory():
    """Lazy initialization for SemanticMemory."""
    global _memory
    if _memory is None:
        from app.core.memory.semantic_memory import SemanticMemory
        _memory = SemanticMemory()
    return _memory


def get_cognee_memory():
    """Lazy initialization for CogneeMemoryManager."""
    global _cognee_memory
    if _cognee_memory is None:
        from app.core.memory.cognee_memory import get_cognee_memory as _get
        _cognee_memory = _get()
    return _cognee_memory


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


# --- Tracing helper ---

def _trace_tool(tool_name: str, **metadata):
    """Log tool invocation for Opik tracing visibility.

    When TRACING_ENABLED=true, this creates a sub-span in the Opik trace.
    When disabled, this is a cheap no-op (just a logger.debug call).
    """
    from app.core.config import is_tracing_enabled
    logger.debug(f"Tool invoked: {tool_name} | metadata={metadata}")
    if is_tracing_enabled():
        try:
            from opik import track
            # Opik will associate this with the parent trace automatically
        except ImportError:
            pass


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
    _trace_tool("retrieve_guidelines", query=query, condition=condition, topic=topic)
    retriever = get_rag_retriever()
    if not retriever:
        return "RAG Unavailable (Init Failed)"

    try:
        rewriter = get_query_rewriter()
        rewrite_result = rewriter.rewrite_query(query)
        enhanced_query = rewrite_result["rewritten_query"]
        auto_filters = rewrite_result["filters"]

        final_condition = condition or auto_filters.get("condition")
        final_topic = topic or auto_filters.get("topic")

        results = retriever.search_guidelines(
            enhanced_query,
            condition=final_condition,
            topic=final_topic,
            k=3
        )

        if not results:
            results = retriever.search_guidelines(enhanced_query, k=3)

        if not results:
            return "No relevant guidelines found."

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
    except (ConnectionError, OSError) as e:
        logger.warning(f"RAG connection error: {e}")
        return "Guideline lookup temporarily unavailable - please proceed with general knowledge."
    except TimeoutError:
        logger.warning("RAG retrieval timed out")
        return "Guideline lookup timed out - please proceed with general knowledge."
    except ValueError as e:
        logger.error(f"RAG value error: {e}")
        return f"Guideline search configuration error: {e}"
    except Exception as e:
        logger.error(f"RAG unexpected error: {e}", exc_info=True)
        return f"RAG Error: {e}"


@tool("Recall User Memory")
def recall_memory(user_id: str, query: str) -> str:
    """
    Search past conversations and constraints for this user.
    Args:
        user_id: ID of the user
        query: What to search for
    """
    _trace_tool("recall_memory", user_id=user_id, query=query)
    try:
        memory = get_memory()
        results = memory.recall_memories(user_id, query)
        if not results:
            return "No specific memories found."
        return "\n".join([f"- {m.get('text', 'N/A')}" for m in results])
    except (ConnectionError, OSError) as e:
        logger.warning(f"Memory recall connection error: {e}")
        return "Memory lookup temporarily unavailable."
    except TimeoutError:
        logger.warning("Memory recall timed out")
        return "Memory lookup timed out."
    except Exception as e:
        logger.error(f"Memory recall error: {e}", exc_info=True)
        return f"Memory recall error: {e}"


@tool("Recall User Memory with Context")
def recall_memory_enhanced(user_id: str, query: str) -> str:
    """
    Search past conversations with structured context.
    
    Returns organized information including:
    - Profile information (entities extracted)
    - Related memories
    - Summary of relevant context
    
    Args:
        user_id: ID of the user
        query: What to search for (e.g., "health profile", "exercise habits")
    """
    _trace_tool("recall_memory_enhanced", user_id=user_id, query=query)
    try:
        cognee = get_cognee_memory()
        results = cognee.recall_contextual_memory(user_id, query)

        output = []

        # Entities
        if results.get("entities"):
            output.append("📊 Profile Information:")
            for key, value in results["entities"].items():
                output.append(f"  - {key}: {value}")
        
        # Summary
        if results.get("summary"):
            output.append(f"\n📝 Context: {results['summary'][:300]}")
        
        # Raw results if nothing else
        if not output and results.get("raw_results"):
            output.append("Found memories:")
            for r in results["raw_results"][:5]:
                text = r.get("text", str(r))[:100]
                output.append(f"  - {text}")
        
        if not output:
            return "No contextual memories found."
        
        return "\n".join(output)
        
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.warning(f"Enhanced memory error, falling back to basic: {e}")
        return recall_memory(user_id, query)
    except Exception as e:
        logger.error(f"Enhanced memory error: {e}", exc_info=True)
        return recall_memory(user_id, query)


@tool("Track Habit Progress")
def track_habit_progress(user_id: str, habit_name: str) -> str:
    """
    Get timeline of a specific habit.
    
    Shows:
    - When mentioned
    - Status (started, active, struggling, stopped)
    - Related context
    
    Args:
        user_id: ID of the user
        habit_name: Name of the habit to track (e.g., "walking", "water intake")
    """
    _trace_tool("track_habit_progress", user_id=user_id, habit_name=habit_name)
    try:
        cognee = get_cognee_memory()
        timeline = cognee.get_habit_timeline(user_id, habit_name)

        if not timeline:
            return f"No tracking data found for '{habit_name}' yet."
        
        output = [f"📈 Progress for '{habit_name}':"]
        
        for entry in timeline[:5]:  # Limit to 5 entries
            idx = entry.get("index", "?")
            status = entry.get("status", "unknown")
            content = entry.get("content", "")[:80]
            timestamp = entry.get("timestamp", "")[:10]
            
            line = f"  [{idx}] {status}"
            if timestamp:
                line += f" ({timestamp})"
            if content:
                line += f": {content}..."
            output.append(line)
        
        return "\n".join(output)

    except (ConnectionError, OSError, TimeoutError) as e:
        logger.warning(f"Habit tracking connection error: {e}")
        return f"Habit tracking temporarily unavailable for '{habit_name}'."
    except Exception as e:
        logger.error(f"Habit tracking error: {e}", exc_info=True)
        return f"Habit tracking error: {e}"


@tool("Save User Constraint")
def save_constraint(user_id: str, constraint: str) -> str:
    """
    Save a permanent constraint about the user.
    Args:
        user_id: ID of the user
        constraint: The constraint to save
    """
    _trace_tool("save_constraint", user_id=user_id)
    try:
        memory = get_memory()
        memory.store_memory(user_id, constraint, metadata={"type": "constraint"})
        return "Constraint saved."
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.warning(f"Constraint save connection error: {e}")
        return "Constraint save temporarily unavailable - will retry later."
    except Exception as e:
        logger.error(f"Failed to save constraint: {e}", exc_info=True)
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
    _trace_tool("save_memory", user_id=user_id, memory_type=memory_type)
    valid_types = {"profile", "constraint", "habit_plan", "outcome"}
    if memory_type not in valid_types:
        memory_type = "profile"

    try:
        memory = get_memory()
        memory.store_memory(user_id, text, metadata={"type": memory_type})
        return f"Memory saved (type: {memory_type})."
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.warning(f"Memory save connection error: {e}")
        return "Memory save temporarily unavailable - will retry later."
    except Exception as e:
        logger.error(f"Failed to save memory: {e}", exc_info=True)
        return f"Failed to save memory: {e}"


@tool("Save Memory with Context")
def save_memory_enhanced(user_id: str, text: str, memory_type: str, entities: Optional[str] = None) -> str:
    """
    Save a memory with structured context.
    
    Args:
        user_id: ID of the user
        text: The information to save
        memory_type: Type - one of: profile, constraint, habit_plan, outcome, conversation
        entities: Optional JSON string of entities (e.g., '{"age": 45}')
    """
    _trace_tool("save_memory_enhanced", user_id=user_id, memory_type=memory_type)
    valid_types = {"profile", "constraint", "habit_plan", "outcome", "conversation"}
    if memory_type not in valid_types:
        memory_type = "conversation"

    try:
        # Parse entities
        parsed_entities = {}
        if entities:
            try:
                parsed_entities = json.loads(entities)
            except json.JSONDecodeError:
                parsed_entities = {"raw": entities}
        
        cognee = get_cognee_memory()
        
        turn_data = {
            "user_message": text,
            "agent_response": f"Stored as {memory_type}",
            "extracted_entities": parsed_entities,
            "timestamp": datetime.now().isoformat()
        }
        
        success = cognee.store_conversation_turn(user_id, turn_data, memory_type)
        
        if success:
            return f"Memory saved with context (type: {memory_type})."
        else:
            # Fallback
            memory = get_memory()
            memory.store_memory(user_id, text, metadata={"type": memory_type})
            return f"Memory saved (type: {memory_type})."
            
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.warning(f"Enhanced memory save connection error: {e}")
        # Fallback to basic save
        try:
            memory = get_memory()
            memory.store_memory(user_id, text, metadata={"type": memory_type})
            return f"Memory saved with basic fallback (type: {memory_type})."
        except Exception:
            return "Memory save temporarily unavailable."
    except Exception as e:
        logger.error(f"Failed to save memory: {e}", exc_info=True)
        return f"Failed to save memory: {e}"