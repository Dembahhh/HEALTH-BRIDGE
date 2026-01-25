import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

# Set your Gemini API key (get it from https://aistudio.google.com/app/apikey)
os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"

from app.services.chat import ChatService

def test_full_flow():
    print(">>> Initializing ChatService...")
    service = ChatService()
    
    user_input = "I am a 45 year old male, I smoke, and my father had hypertension. I work night shifts and can't go to the gym."
    user_id = "test_user_001"
    
    print(f">>> Running Intake Session for input: '{user_input}'")
    try:
        result = service.run_intake_session(user_input, user_id)
        print("\n>>> Result received!")
        print(result)
        
        print("\n>>> Validation:")
        if result:
            print("SUCCESS: Result returned.")
        else:
            print("FAILURE: Validation empty.")
            
    except Exception as e:
        print(f"FAILURE: Execution crashed: {e}")
        # Print stack trace if needed, but for now just the error
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_flow()
