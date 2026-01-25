"""
API Dependencies

Common dependencies for API routes (auth, database, etc.).
"""

from typing import Annotated
from fastapi import Depends
from app.services.auth import get_current_user

# Re-export key dependencies
CurrentUser = Annotated[dict, Depends(get_current_user)]
