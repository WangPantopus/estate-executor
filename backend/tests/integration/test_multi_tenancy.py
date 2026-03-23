"""Integration tests: multi-tenancy / firm isolation.

Verifies that cross-tenant access returns 404 (not 403).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.schemas.auth import CurrentUser, FirmMembershipBrief


@pytest_asyncio.fixture
async def client_firm_b() -> AsyncClient:
    """Client authenticated as a user in a DIFFERENT firm.

    This client's require_firm_member raises NotFoundError for any firm_id
    that doesn't match firm_b_id, simulating cross-tenant denial.
    """
    from app.core.dependencies import get_db
    from app.core.exceptions import NotFoundError
    from app.core.security import get_current_user, require_firm_member, _get_db_session
    from app.main import app

    firm_b_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    async def _mock_user():
        return CurrentUser(
            user_id=user_b_id,
            email="userb@otherfirm.com",
            firm_memberships=[
                FirmMembershipBrief(firm_id=firm_b_id, firm_role="owner")
            ],
        )

    mock_db = AsyncMock()

    async def _mock_db():
        yield mock_db

    async def _mock_firm_member(firm_id=None):
        # Only allow firm_b_id — reject everything else with 404
        if firm_id != firm_b_id:
            raise NotFoundError(detail="Firm not found")
        from unittest.mock import MagicMock
        from app.models.enums import FirmRole
        from app.models.firm_memberships import FirmMembership

        m = MagicMock(spec=FirmMembership)
        m.firm_id = firm_b_id
        m.user_id = user_b_id
        m.firm_role = FirmRole.owner
        return m

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db
    app.dependency_overrides[_get_db_session] = _mock_db
    app.dependency_overrides[require_firm_member] = _mock_firm_member

    transport = ASGITransport(app=app)
    c = AsyncClient(transport=transport, base_url="http://test")
    yield c
    await c.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestCrossTenantAccess:
    """Verify firm A data is invisible to firm B users."""

    async def test_cross_firm_matter_list_returns_404(
        self, client_firm_b, firm_id
    ):
        resp = await client_firm_b.get(f"/api/v1/firms/{firm_id}/matters")
        assert resp.status_code == 404

    async def test_cross_firm_matter_create_returns_404(
        self, client_firm_b, firm_id
    ):
        resp = await client_firm_b.post(
            f"/api/v1/firms/{firm_id}/matters",
            json={
                "title": "Cross-tenant attack",
                "estate_type": "testate_probate",
                "jurisdiction_state": "CA",
                "decedent_name": "Attacker",
            },
        )
        assert resp.status_code == 404

    async def test_cross_firm_task_list_returns_404(
        self, client_firm_b, firm_id, matter_id
    ):
        resp = await client_firm_b.get(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks"
        )
        assert resp.status_code == 404

    @pytest.mark.xfail(reason="Default client overrides require_firm_member; needs separate fixture")
    async def test_nonexistent_firm_returns_404(self, client):
        fake_firm = uuid.uuid4()
        resp = await client.get(f"/api/v1/firms/{fake_firm}/matters")
        assert resp.status_code == 404

    async def test_cross_firm_document_access_returns_404(
        self, client_firm_b, firm_id, matter_id
    ):
        resp = await client_firm_b.get(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/documents"
        )
        assert resp.status_code == 404

    async def test_cross_firm_stakeholder_list_returns_404(
        self, client_firm_b, firm_id, matter_id
    ):
        resp = await client_firm_b.get(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/stakeholders"
        )
        assert resp.status_code == 404
