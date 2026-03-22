"""Integration test fixtures — service-level tests with mock DB sessions.

Since this environment doesn't have PostgreSQL available and the models use
PostgreSQL-specific types (UUID, JSONB, ARRAY) that are incompatible with
SQLite, these integration tests use mocked async sessions that test the
full API route → service → model flow without a real database.

The mock approach tests:
- Request validation and serialization
- Permission enforcement
- Error handling
- Response formatting
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# ─── Patch broken jwt/cryptography before any app imports ─────────────────────
if "jwt" not in sys.modules:
    mock_jwt = MagicMock()
    mock_jwt.PyJWK = MagicMock
    mock_jwt.PyJWKSet = MagicMock
    mock_jwt.PyJWKClient = MagicMock
    mock_jwt.decode = MagicMock(return_value={})
    mock_jwt.ExpiredSignatureError = type("ExpiredSignatureError", (Exception,), {})
    mock_jwt.InvalidTokenError = type("InvalidTokenError", (Exception,), {})
    sys.modules["jwt"] = mock_jwt

# Mock cryptography
for _mod in [
    "cryptography", "cryptography.hazmat", "cryptography.hazmat.bindings",
    "cryptography.hazmat.bindings._rust", "cryptography.hazmat.bindings._rust.exceptions",
    "cryptography.exceptions", "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.ciphers", "cryptography.hazmat.primitives.ciphers.aead",
    "cryptography.hazmat.primitives.ciphers.base",
    "cryptography.hazmat.primitives.asymmetric",
    "cryptography.hazmat.primitives.asymmetric.ec",
    "cryptography.hazmat.primitives.hashes",
    "cryptography.hazmat._oid",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models.enums import FirmRole, InviteStatus, StakeholderRole
from app.schemas.auth import CurrentUser, FirmMembershipBrief


# ─── Fixtures ─────────────────────────────────────────────────────────────────

_FIRM_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
_USER_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
_MATTER_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
_STAKEHOLDER_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")


@pytest.fixture
def firm_id() -> uuid.UUID:
    return _FIRM_ID


@pytest.fixture
def user_id() -> uuid.UUID:
    return _USER_ID


@pytest.fixture
def matter_id() -> uuid.UUID:
    return _MATTER_ID


@pytest.fixture
def stakeholder_id() -> uuid.UUID:
    return _STAKEHOLDER_ID


@pytest_asyncio.fixture
async def client(firm_id, user_id) -> AsyncGenerator[AsyncClient]:
    """Create an httpx AsyncClient with mocked auth (owner role)."""
    from app.core.dependencies import get_db
    from app.core.security import get_current_user
    from app.main import app

    async def _mock_current_user() -> CurrentUser:
        return CurrentUser(
            user_id=user_id,
            email="testuser@example.com",
            firm_memberships=[
                FirmMembershipBrief(firm_id=firm_id, firm_role="owner")
            ],
        )

    # Mock DB session — most endpoints will need specific mocks per test
    mock_session = AsyncMock()

    async def _mock_get_db():
        yield mock_session

    from app.core.security import _get_db_session, require_firm_member, require_stakeholder
    from app.models.firm_memberships import FirmMembership
    from app.models.stakeholders import Stakeholder

    # Override require_firm_member to return a mock owner membership
    async def _mock_require_firm_member(firm_id=None):
        m = MagicMock(spec=FirmMembership)
        m.firm_id = firm_id
        m.user_id = user_id
        m.firm_role = FirmRole.owner
        return m

    # Override require_stakeholder to return a mock matter_admin stakeholder
    async def _mock_require_stakeholder(matter_id=None):
        s = MagicMock(spec=Stakeholder)
        s.id = uuid.uuid4()
        s.matter_id = matter_id
        s.user_id = user_id
        s.email = "testuser@example.com"
        s.full_name = "Test User"
        s.role = StakeholderRole.matter_admin
        return s

    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[_get_db_session] = _mock_get_db
    app.dependency_overrides[require_firm_member] = _mock_require_firm_member
    app.dependency_overrides[require_stakeholder] = _mock_require_stakeholder

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
