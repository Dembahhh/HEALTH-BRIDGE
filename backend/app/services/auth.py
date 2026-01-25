import os
from typing import Optional
from fastapi import Header, HTTPException, Depends

# Try importing firebase_admin, but gracefully fail if not installed/configured
try:
    import firebase_admin
    from firebase_admin import auth, credentials
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# Initialize Firebase (singleton pattern)
if FIREBASE_AVAILABLE:
    try:
        # Check if already initialized
        if not firebase_admin._apps:
            # Look for checking credentials path env var
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                # Default logic or warning
                print("Warning: Firebase Credentials not found. Auth may fail unless skipped.")
                # For hackathon/testing, maybe initialize with no creds (relies on Google Application Default Credentials)
                # firebase_admin.initialize_app()
    except Exception as e:
        print(f"Firebase Init Error: {e}")

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to verify the Firebase ID token from the Authorization header.
    Returns the decoded token dict (user info).
    """
    
    # DEV BYPASS: If explicitly disabled in env
    if os.getenv("SKIP_AUTH", "false").lower() == "true":
        return {"uid": "dev_user_123", "email": "dev@example.com", "name": "Dev User"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header")

    token = authorization.split("Bearer ")[1]

    if not FIREBASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Firebase Admin SDK not installed.")

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
