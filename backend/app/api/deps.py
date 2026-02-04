"""
API Dependencies

Common dependencies for API routes (auth, database, etc.).
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# Firebase auth bearer
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
) -> dict:
    """
    Verify Firebase ID token and return current user.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        from firebase_admin import auth
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        email = decoded_token.get('email')
        
    except Exception as e:
        print(f"Auth Error: {e}")
        # Only allow dev token in development with explicit env var
        if os.getenv("ENV") == "development" and os.getenv("ALLOW_DEV_TOKEN", "false").lower() == "true":
            if token == os.getenv("DEV_TOKEN"):  # Read from env instead of hardcoding
                return {"uid": "dev-user", "email": "dev@example.com"}

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find or Create User in MongoDB
    try:
        from app.models.user import User
        user = await User.find_one(User.firebase_uid == uid)
        
        if not user:
            user = User(
                email=email,
                firebase_uid=uid,
                display_name=decoded_token.get('name'),
            )
            await user.create()
            
        return user if user else {"uid": uid, "email": email}
        
    except Exception as e:
        print(f"User DB Error: {e}")
        # Fallback if DB fails but token valid
        return {"uid": uid, "email": email}


# Type alias for dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user)]
