"""JWT validation and permission checking utilities."""

from typing import Any


async def verify_jwt(token: str) -> dict[str, Any]:
    """Verify and decode a JWT token from Auth0.

    TODO: Implement Auth0 JWT validation in Prompt 002.
    """
    raise NotImplementedError("JWT validation not yet implemented")


def check_permission(user_permissions: list[str], required: str) -> bool:
    """Check if a user has the required permission."""
    return required in user_permissions
