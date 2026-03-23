"""Authentication and authorization schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from uuid import UUID


class FirmMembershipBrief(BaseModel):
    """Brief firm membership info for the current user."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "firm_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "firm_role": "admin",
                }
            ]
        },
    )

    firm_id: UUID
    firm_role: str


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "sub": "auth0|abc123",
                    "email": "admin@lawfirm.com",
                    "firm_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
                    "roles": {"a1b2c3d4-e5f6-7890-abcd-ef1234567890": "admin"},
                }
            ]
        },
    )

    sub: str
    email: str
    firm_ids: list[str]
    roles: dict[str, str]


class CurrentUser(BaseModel):
    """Authenticated user context."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "email": "admin@lawfirm.com",
                    "firm_memberships": [
                        {
                            "firm_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "firm_role": "admin",
                        }
                    ],
                }
            ]
        },
    )

    user_id: UUID
    email: str
    firm_memberships: list[FirmMembershipBrief]
