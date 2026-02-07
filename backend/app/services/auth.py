"""
Auth utilities (DEPRECATED - use app.api.deps.get_current_user for API routes).

This module is only kept for backwards compatibility.
All API routes should import from app.api.deps instead.
"""

import warnings

warnings.warn(
    "app.services.auth is deprecated. Use app.api.deps.CurrentUser for API routes.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from the canonical location
from app.api.deps import get_current_user, CurrentUser  # noqa: F401
