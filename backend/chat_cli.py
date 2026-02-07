#!/usr/bin/env python3
"""
HEALTH-BRIDGE CLI Chat Interface

Phase 5: Fully integrated with all components:
- Session management
- LLM-based extraction
- Pattern detection
- Intervention generation

Usage:
    python chat_cli.py --intake     # New user health assessment
    python chat_cli.py --followup   # Returning user check-in
    python chat_cli.py --general    # General health questions
"""

import argparse
import sys
import os
import uuid
from datetime import datetime
from typing import Optional, List

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.services.session_manager import SessionManager, create_session_manager


def clear_user_memories(user_id: str) -> int:
    """Clear all memories for a user. Useful for testing."""
    try:
        from app.core.memory.semantic_memory import SemanticMemory
        memory = SemanticMemory()
        count = memory.clear_user_memories(user_id)
        return count
    except Exception as e:
        print(f"Error clearing memories: {e}")
        return 0


def print_banner(session_id: str = None):
    """Print welcome banner."""
    print("\n" + "=" * 60)
    print("   HEALTH-BRIDGE - AI Health Assistant")
    print("=" * 60)
    print("  Type 'quit' or 'exit' to end the session")
    print("  Type 'status' to see collected information")
    print("  Type 'patterns' to see detected patterns (follow-up)")
    print("  Type 'clear' to clear all memories (for testing)")
    if session_id:
        print(f"  Session: {session_id[:8]}...")
    print("=" * 60 + "\n")


def print_status(manager: SessionManager):
    """Print current session status."""
    print("\n" + "-" * 40)
    print(" Session Status:")
    print(f"   Type: {manager.session_type}")
    print(f"   Turn: {manager.state.turn_count}")
    print(f"   Fields collected: {len(manager.state.collected_fields)}")

    if manager.state.collected_fields:
        print("\n   Collected data:")
        for name, field in manager.state.collected_fields.items():
            print(f"   - {name}: {field.value} ({field.confidence.value})")

    if manager.state.implied_fields:
        print("\n   Implied information:")
        for name, value in manager.state.implied_fields.items():
            print(f"   - {name}: {value}")

    print("-" * 40 + "\n")


def print_patterns(manager: SessionManager):
    """Print detected patterns."""
    print("\n" + "-" * 40)
    print(" Detected Patterns:")

    if manager.patterns_detected:
        for pattern in manager.patterns_detected:
            print(f"\n   [{pattern.severity.value.upper()}] {pattern.pattern_type.value}")
            print(f"   {pattern.description}")
            if pattern.recommendation:
                print(f"    {pattern.recommendation}")
    else:
        print("   No patterns detected yet.")

    print("-" * 40 + "\n")


def run_crew(manager: SessionManager) -> str:
    """Run the CrewAI crew with session context."""
    try:
        from app.services.chat import ChatService

        chat_service = ChatService()
        context = manager.get_session_context()

        # Run appropriate crew
        result = chat_service.run_session(
            user_input=context["combined_input"],
            user_id=context["user_id"],
            session_type=context["session_type"],
            detected_fields=context["collected_fields"],
            conversation_history=manager.state.get_user_messages()
        )

        return manager.complete_session(result)

    except Exception as e:
        print(f"\n Error running health analysis: {e}")
        return f"I encountered an issue processing your information. Error: {e}"


def get_user_habits(user_id: str) -> List[str]:
    """Retrieve user's existing habits from memory."""
    try:
        from app.core.memory.semantic_memory import SemanticMemory
        import json

        memory = SemanticMemory()
        results = memory.recall_memories(user_id, "habit plan", k=3)

        habits = []
        for r in results:
            text = r.get("text", "")
            try:
                parsed = json.loads(text)
                if "habits" in parsed:
                    for h in parsed["habits"]:
                        if isinstance(h, dict):
                            habits.append(h.get("title", h.get("description", str(h))))
                        else:
                            habits.append(str(h))
            except (json.JSONDecodeError, TypeError):
                # Extract habits from plain text
                if "walk" in text.lower():
                    habits.append("Walking")
                if "exercise" in text.lower():
                    habits.append("Exercise")

        return habits[:5]  # Return up to 5 habits

    except Exception as e:
        print(f"Note: Could not retrieve previous habits: {e}")
        return []


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="HEALTH-BRIDGE CLI Chat")
    parser.add_argument("--intake", action="store_true", help="Start intake session")
    parser.add_argument("--followup", action="store_true", help="Start follow-up session")
    parser.add_argument("--general", action="store_true", help="Start general Q&A session")
    parser.add_argument("--user", type=str, default="cli_user", help="User ID")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM extraction (use regex)")
    parser.add_argument("--clear", action="store_true", help="Clear user memories before starting (for testing)")
    parser.add_argument("--new-session", action="store_true", help="Generate new session ID (isolate from past conversations)")

    args = parser.parse_args()

    # Generate session ID for isolation
    session_id = str(uuid.uuid4()) if args.new_session else None

    # Clear memories if requested (useful for testing different scenarios)
    if args.clear:
        count = clear_user_memories(args.user)
        print(f" Cleared {count} memories for user '{args.user}'")

    # Determine session type
    if args.followup:
        session_type = "follow_up"
    elif args.general:
        session_type = "general"
    else:
        session_type = "intake"

    # Get user habits for follow-up
    user_habits = []
    if session_type == "follow_up":
        user_habits = get_user_habits(args.user)

    # Create session manager
    manager = create_session_manager(
        user_id=args.user,
        session_type=session_type,
        user_habits=user_habits,
        use_llm=not args.no_llm
    )

    # Print banner
    print_banner(session_id)

    # Show welcome message
    welcome = manager.get_welcome_message()
    print(f" Assistant: {welcome}\n")

    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input(" You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n Thank you for using HEALTH-BRIDGE. Take care of your health!")
                break

            if user_input.lower() == "status":
                print_status(manager)
                continue

            if user_input.lower() == "patterns":
                print_patterns(manager)
                continue

            if user_input.lower() == "reset":
                manager.reset()
                welcome = manager.get_welcome_message()
                print(f"\n Session reset.\n\n Assistant: {welcome}\n")
                continue

            if user_input.lower() == "clear":
                count = clear_user_memories(args.user)
                manager.reset()
                welcome = manager.get_welcome_message()
                print(f"\n Cleared {count} memories. Session reset.\n\n Assistant: {welcome}\n")
                continue

            # Process message
            result = manager.process_message(user_input)

            # Handle urgent symptoms
            if result.has_urgent_symptoms:
                print(f"\n Assistant: {result.response}\n")
                print("  Please address this before continuing.\n")
                continue

            # Check if ready for crew
            if result.ready_for_crew:
                print(f"\n Assistant: {result.response}\n")
                print(" Processing...\n")

                # Run crew
                final_response = run_crew(manager)

                print("-" * 60)
                print(f"\n Assistant:\n{final_response}\n")
                print("-" * 60)

                # Show patterns if any
                if result.patterns:
                    print("\n Patterns Detected:")
                    for p in result.patterns[:3]:
                        print(f"   • {p.get('description', 'Unknown')}")

                # Ask if user wants to continue
                print("\n Session complete!")
                continue_choice = input("Would you like to continue chatting? (yes/no): ").strip().lower()

                if continue_choice in ["yes", "y"]:
                    manager.reset()
                    manager.session_type = "general"
                    print("\n🤖 Assistant: How else can I help you today?\n")
                else:
                    print("\n👋 Thank you for using HEALTH-BRIDGE. Take care!")
                    break
            else:
                # Continue conversation
                print(f"\n Assistant: {result.response}\n")

        except KeyboardInterrupt:
            print("\n\n Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n Error: {e}")
            print("Please try again.\n")


if __name__ == "__main__":
    main()
