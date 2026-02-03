"""
Interactive CLI for chatting with HealthBridge agents.

Guides users through providing sufficient information via a multi-turn
conversation before running the full CrewAI pipeline. Asks one question
at a time and waits for user responses. This prevents wasting LLM tokens
on vague or insufficient input.

Usage:
    python chat_cli.py                  # default general session
    python chat_cli.py --intake         # force intake session
    python chat_cli.py --follow_up      # force follow-up session
    python chat_cli.py --general        # force general/educational session
"""

import os
import sys

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


def main():
    session_type = "general"
    if "--intake" in sys.argv:
        session_type = "intake"
    elif "--follow_up" in sys.argv:
        session_type = "follow_up"
    elif "--general" in sys.argv:
        session_type = "general"

    print("=" * 60)
    print("  HealthBridge AI - Interactive Chat")
    print(f"  Session: {session_type} | User: {USER_ID}")
    print("  Commands: 'quit' to exit, 'switch <type>' to change session")
    print("=" * 60)

    service = ChatService()
    collector = InputCollector()

    # For follow-up, we'd normally fetch user's actual habits from DB
    user_habits = MOCK_USER_HABITS if session_type == "follow_up" else None

    # Show initial welcome question
    welcome = collector.get_welcome_question(session_type, user_habits)
    print(f"\nHealthBridge: {welcome}")

    conversation_history: list[str] = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("Goodbye.")
            break

        if user_input.lower().startswith("switch "):
            new_type = user_input.split(" ", 1)[1].strip()
            if new_type in ("intake", "follow_up", "general"):
                session_type = new_type
                conversation_history = []
                user_habits = MOCK_USER_HABITS if session_type == "follow_up" else None
                welcome = collector.get_welcome_question(session_type, user_habits)
                print(f"\nSwitched to: {session_type}")
                print(f"\nHealthBridge: {welcome}")
            else:
                print("Valid types: intake, follow_up, general")
            continue

        # Accumulate messages and assess sufficiency
        conversation_history.append(user_input)
        assessment = collector.assess(conversation_history, session_type, user_habits)

        if not assessment["ready"]:
            # Not enough info yet — ask the next question and wait
            print(f"\nHealthBridge: {assessment['question']}")
            continue

        # Sufficient input collected — run the crew
        combined_input = assessment["combined_input"]
        fields = assessment.get("detected_fields", {})
        detected_count = sum(1 for v in fields.values() if v)

        print(f"\n[Collected {detected_count} data points over {assessment['turn']} message(s)]")
        print(f"[Running {session_type} crew — this may take 30-60 seconds...]\n")

        try:
            result = service.run_session(
                combined_input, USER_ID, session_type=session_type
            )
            print(f"HealthBridge: {result}")

            if hasattr(result, "habits") and result.habits:
                print(f"\n[Extracted {len(result.habits)} habits]")

        except Exception as e:
            print(f"\nError: {e}")

        # Reset for next conversation round
        conversation_history = []
        print("\n" + "-" * 60)
        print("Session complete. You can continue chatting or type 'quit' to exit.")

        # Show fresh welcome for next round
        welcome = collector.get_welcome_question(session_type, user_habits)
        print(f"\nHealthBridge: {welcome}")


if __name__ == "__main__":
    main()
