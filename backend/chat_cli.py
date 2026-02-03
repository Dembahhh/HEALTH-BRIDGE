"""
Interactive CLI for chatting with HealthBridge agents.

Guides users through providing sufficient information via a multi-turn
conversation before running the full CrewAI pipeline. Asks one question
at a time and waits for user responses. This prevents wasting LLM tokens
on vague or insufficient input.

PHASE 1 IMPROVEMENTS:
- Conversation history preserved across sessions
- Session state tracking
- Memory debug commands
- Better context passing to agents

Usage:
    python chat_cli.py                  # default general session
    python chat_cli.py --intake         # force intake session
    python chat_cli.py --follow_up      # force follow-up session
    python chat_cli.py --general        # force general/educational session
    python chat_cli.py --debug          # enable debug mode
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.services.chat import ChatService
from app.services.input_collector import InputCollector

USER_ID = "cli_user"

# Mock user habits for follow-up demo (in production, fetch from DB)
MOCK_USER_HABITS = [
    "Walk 20 minutes after dinner",
    "Drink 8 glasses of water daily",
    "Reduce salt in cooking",
    "Take blood pressure reading weekly",
]


@dataclass
class SessionState:
    """
    Tracks conversation state across multiple turns and sessions.
    
    PHASE 1: This replaces the simple list that was reset after each crew run.
    """
    session_type: str = "general"
    current_turn_history: List[str] = field(default_factory=list)
    all_session_history: List[Dict] = field(default_factory=list)  # Persists across crew runs
    detected_fields: Dict = field(default_factory=dict)
    sessions_completed: int = 0
    user_habits: Optional[List[str]] = None
    
    def add_message(self, message: str):
        """Add a user message to current turn."""
        self.current_turn_history.append(message)
    
    def complete_session(self, result: str, detected_fields: Dict):
        """Mark a session as complete and archive the conversation."""
        self.all_session_history.append({
            "session_type": self.session_type,
            "messages": self.current_turn_history.copy(),
            "detected_fields": detected_fields,
            "result_preview": result[:200] if result else ""
        })
        self.sessions_completed += 1
        # DON'T clear current_turn_history - keep for context
        # Instead, mark a session boundary
        self.current_turn_history.append(f"[SESSION {self.sessions_completed} COMPLETE]")
    
    def get_recent_context(self, max_messages: int = 10) -> List[str]:
        """Get recent messages for context, excluding session markers."""
        recent = []
        for msg in reversed(self.current_turn_history):
            if not msg.startswith("[SESSION"):
                recent.insert(0, msg)
                if len(recent) >= max_messages:
                    break
        return recent
    
    def switch_session_type(self, new_type: str):
        """Switch to a different session type."""
        self.session_type = new_type
        # Keep history but note the switch
        self.current_turn_history.append(f"[SWITCHED TO {new_type.upper()}]")
    
    def reset(self):
        """Full reset - use sparingly."""
        self.current_turn_history = []
        self.all_session_history = []
        self.detected_fields = {}
        self.sessions_completed = 0


def show_memory_debug(user_id: str):
    """Show stored memories for debugging."""
    try:
        from app.core.memory.semantic_memory import SemanticMemory
        memory = SemanticMemory()
        
        all_memories = memory.get_all_memories(user_id)
        
        print("\n" + "=" * 60)
        print(f"  MEMORY DEBUG - User: {user_id}")
        print(f"  Total memories: {len(all_memories)}")
        print("=" * 60)
        
        if not all_memories:
            print("  No memories stored.")
        else:
            for i, mem in enumerate(all_memories, 1):
                mem_type = mem.get("metadata", {}).get("type", "unknown")
                timestamp = mem.get("metadata", {}).get("timestamp", "unknown")
                text_preview = mem.get("text", "")[:100]
                print(f"\n  [{i}] Type: {mem_type}")
                print(f"      Time: {timestamp}")
                print(f"      Text: {text_preview}...")
        
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"\n  Memory debug error: {e}")


def clear_memories(user_id: str):
    """Clear all memories for a user."""
    try:
        from app.core.memory.semantic_memory import SemanticMemory
        memory = SemanticMemory()
        
        count = memory.clear_user_memories(user_id)
        print(f"\n  Cleared {count} memories for user '{user_id}'.")
    except Exception as e:
        print(f"\n  Error clearing memories: {e}")


def main():
    # Parse arguments
    session_type = "general"
    debug_mode = "--debug" in sys.argv
    
    if "--intake" in sys.argv:
        session_type = "intake"
    elif "--follow_up" in sys.argv:
        session_type = "follow_up"
    elif "--general" in sys.argv:
        session_type = "general"

    print("=" * 60)
    print("  HealthBridge AI - Interactive Chat")
    print(f"  Session: {session_type} | User: {USER_ID}")
    print("  Commands:")
    print("    'quit'          - Exit the program")
    print("    'switch <type>' - Change session (intake/follow_up/general)")
    print("    'memory'        - Show stored memories")
    print("    'clear'         - Clear all memories")
    print("    'reset'         - Reset conversation state")
    print("    'status'        - Show current session state")
    print("=" * 60)

    service = ChatService()
    collector = InputCollector()

    # Initialize session state
    state = SessionState(
        session_type=session_type,
        user_habits=MOCK_USER_HABITS if session_type == "follow_up" else None
    )

    # Show initial welcome question
    welcome = collector.get_welcome_question(state.session_type, state.user_habits)
    print(f"\nHealthBridge: {welcome}")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.lower() == "quit":
            print("Goodbye.")
            break
        
        if user_input.lower() == "memory":
            show_memory_debug(USER_ID)
            continue
        
        if user_input.lower() == "clear":
            clear_memories(USER_ID)
            continue
        
        if user_input.lower() == "reset":
            state.reset()
            welcome = collector.get_welcome_question(state.session_type, state.user_habits)
            print("\n  Session state reset.")
            print(f"\nHealthBridge: {welcome}")
            continue
        
        if user_input.lower() == "status":
            print(f"\n  Session Type: {state.session_type}")
            print(f"  Current Turn Messages: {len(state.current_turn_history)}")
            print(f"  Sessions Completed: {state.sessions_completed}")
            print(f"  Detected Fields: {state.detected_fields}")
            continue

        if user_input.lower().startswith("switch "):
            new_type = user_input.split(" ", 1)[1].strip()
            if new_type in ("intake", "follow_up", "general"):
                state.switch_session_type(new_type)
                state.user_habits = MOCK_USER_HABITS if new_type == "follow_up" else None
                welcome = collector.get_welcome_question(state.session_type, state.user_habits)
                print(f"\nSwitched to: {state.session_type}")
                print(f"\nHealthBridge: {welcome}")
            else:
                print("Valid types: intake, follow_up, general")
            continue

        # Add message to state
        state.add_message(user_input)
        
        # Get recent context (excludes session markers)
        recent_messages = state.get_recent_context(max_messages=15)
        
        # Assess with conversation history
        assessment = collector.assess(recent_messages, state.session_type, state.user_habits)
        state.detected_fields = assessment.get("detected_fields", {})

        if not assessment["ready"]:
            # Not enough info yet — ask the next question and wait
            print(f"\nHealthBridge: {assessment['question']}")
            continue

        # Sufficient input collected — run the crew
        combined_input = assessment["combined_input"]
        fields = assessment.get("detected_fields", {})
        detected_count = sum(1 for v in fields.values() if v)

        print(f"\n[Collected {detected_count} data points over {assessment['turn']} message(s)]")
        print(f"[Running {state.session_type} crew — this may take 30-60 seconds...]\n")

        try:
            # Pass conversation history for better memory storage
            result = service.run_session(
                user_input=combined_input,
                user_id=USER_ID,
                session_type=state.session_type,
                detected_fields=fields,
                conversation_history=recent_messages
            )
            print(f"HealthBridge: {result}")

            if hasattr(result, "habits") and result.habits:
                print(f"\n[Extracted {len(result.habits)} habits]")
            
            # Mark session complete (but keep history!)
            state.complete_session(str(result), fields)

        except Exception as e:
            print(f"\nError: {e}")
            if debug_mode:
                import traceback
                traceback.print_exc()

        print("\n" + "-" * 60)
        print(f"Session {state.sessions_completed} complete. Continue chatting or type 'quit' to exit.")

        # Show fresh welcome for next round
        welcome = collector.get_welcome_question(state.session_type, state.user_habits)
        print(f"\nHealthBridge: {welcome}")


if __name__ == "__main__":
    main()