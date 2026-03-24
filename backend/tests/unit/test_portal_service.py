"""Unit tests for the beneficiary portal service and schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.models.enums import (
    CommunicationType,
    CommunicationVisibility,
    MatterPhase,
    StakeholderRole,
)


class TestPortalSchemas:
    """Verify portal schema imports and structure."""

    def test_portal_overview_response_fields(self):
        from app.schemas.portal import PortalOverviewResponse

        fields = PortalOverviewResponse.model_fields
        assert "matter" in fields
        assert "your_role" in fields
        assert "contacts" in fields
        assert "milestones" in fields
        assert "distribution" in fields
        assert "firm_name" in fields
        assert "firm_logo_url" in fields

    def test_portal_matter_summary_fields(self):
        from app.schemas.portal import PortalMatterSummary

        fields = PortalMatterSummary.model_fields
        assert "matter_id" in fields
        assert "decedent_name" in fields
        assert "phase" in fields
        assert "completion_percentage" in fields

    def test_portal_document_item_fields(self):
        from app.schemas.portal import PortalDocumentItem

        fields = PortalDocumentItem.model_fields
        assert "id" in fields
        assert "filename" in fields
        assert "doc_type" in fields
        assert "size_bytes" in fields
        assert "shared_at" in fields

    def test_portal_message_item_fields(self):
        from app.schemas.portal import PortalMessageItem

        fields = PortalMessageItem.model_fields
        assert "id" in fields
        assert "sender_name" in fields
        assert "type" in fields
        assert "body" in fields
        assert "requires_acknowledgment" in fields
        assert "acknowledged" in fields

    def test_portal_message_create_fields(self):
        from app.schemas.portal import PortalMessageCreate

        fields = PortalMessageCreate.model_fields
        assert "subject" in fields
        assert "body" in fields

    def test_portal_matter_brief_fields(self):
        from app.schemas.portal import PortalMatterBrief

        fields = PortalMatterBrief.model_fields
        assert "matter_id" in fields
        assert "firm_id" in fields
        assert "decedent_name" in fields
        assert "phase" in fields
        assert "firm_name" in fields

    def test_portal_beneficiary_matters_response(self):
        from app.schemas.portal import PortalBeneficiaryMattersResponse

        fields = PortalBeneficiaryMattersResponse.model_fields
        assert "matters" in fields


class TestPortalSchemaValidation:
    """Test schema instantiation with valid data."""

    def test_create_portal_matter_summary(self):
        from app.schemas.portal import PortalMatterSummary

        summary = PortalMatterSummary(
            matter_id=uuid.uuid4(),
            decedent_name="John Doe",
            estate_type="testate_probate",
            jurisdiction_state="CA",
            phase="administration",
            completion_percentage=45.5,
            estimated_completion=None,
        )
        assert summary.decedent_name == "John Doe"
        assert summary.completion_percentage == 45.5

    def test_create_portal_document_item(self):
        from app.schemas.portal import PortalDocumentItem

        doc = PortalDocumentItem(
            id=uuid.uuid4(),
            filename="death_certificate.pdf",
            doc_type="death_certificate",
            size_bytes=102400,
            shared_at=datetime.now(),
        )
        assert doc.filename == "death_certificate.pdf"

    def test_create_portal_message_item(self):
        from app.schemas.portal import PortalMessageItem

        msg = PortalMessageItem(
            id=uuid.uuid4(),
            sender_name="Jane Attorney",
            type="distribution_notice",
            subject="Distribution Notice",
            body="Your distribution has been processed.",
            created_at=datetime.now(),
            requires_acknowledgment=True,
            acknowledged=False,
        )
        assert msg.requires_acknowledgment is True
        assert msg.acknowledged is False

    def test_create_portal_message_create(self):
        from app.schemas.portal import PortalMessageCreate

        msg = PortalMessageCreate(body="I have a question about the estate.")
        assert msg.subject is None
        assert msg.body == "I have a question about the estate."

    def test_create_portal_message_create_with_subject(self):
        from app.schemas.portal import PortalMessageCreate

        msg = PortalMessageCreate(subject="Question", body="When will this be resolved?")
        assert msg.subject == "Question"

    def test_create_portal_contact_info(self):
        from app.schemas.portal import PortalContactInfo

        contact = PortalContactInfo(
            name="Jane Smith",
            email="jane@lawfirm.com",
            role="Lead Attorney",
        )
        assert contact.name == "Jane Smith"

    def test_create_portal_milestone(self):
        from app.schemas.portal import PortalMilestone

        milestone = PortalMilestone(
            title="Probate filed",
            date="March 1, 2026",
            completed=True,
            is_next=False,
        )
        assert milestone.completed is True

    def test_create_portal_distribution_summary(self):
        from app.schemas.portal import PortalDistributionSummary

        dist = PortalDistributionSummary(
            total_estate_value=None,
            distribution_status="pending",
            notices_count=2,
            pending_acknowledgments=1,
        )
        assert dist.notices_count == 2


class TestPortalServiceMilestoneBuilder:
    """Test the milestone builder helper function."""

    def test_build_milestones_immediate_phase(self):
        from app.services.portal_service import _build_milestones

        class MockMatter:
            phase = MatterPhase.immediate

        milestones = _build_milestones(MockMatter(), [])
        assert len(milestones) == 4  # 4 phases
        # First milestone (immediate) is_next, none completed
        assert milestones[0]["is_next"] is True
        assert milestones[0]["completed"] is False
        assert milestones[1]["completed"] is False

    def test_build_milestones_administration_phase(self):
        from app.services.portal_service import _build_milestones

        class MockMatter:
            phase = MatterPhase.administration

        milestones = _build_milestones(MockMatter(), [])
        assert milestones[0]["completed"] is True  # immediate completed
        assert milestones[1]["is_next"] is True  # administration is current
        assert milestones[1]["completed"] is False

    def test_build_milestones_distribution_phase(self):
        from app.services.portal_service import _build_milestones

        class MockMatter:
            phase = MatterPhase.distribution

        milestones = _build_milestones(MockMatter(), [])
        assert milestones[0]["completed"] is True  # immediate
        assert milestones[1]["completed"] is True  # administration
        assert milestones[2]["is_next"] is True  # distribution is current
        assert milestones[2]["completed"] is False

    def test_build_milestones_closing_phase(self):
        from app.services.portal_service import _build_milestones

        class MockMatter:
            phase = MatterPhase.closing

        milestones = _build_milestones(MockMatter(), [])
        assert milestones[0]["completed"] is True
        assert milestones[1]["completed"] is True
        assert milestones[2]["completed"] is True
        assert milestones[3]["is_next"] is True

    def test_build_milestones_with_communications(self):
        from app.services.portal_service import _build_milestones

        class MockMatter:
            phase = MatterPhase.administration

        class MockComm:
            subject = "Inventory completed"
            created_at = datetime(2026, 3, 15, 10, 0)

        milestones = _build_milestones(MockMatter(), [MockComm()])
        assert len(milestones) == 5  # 4 phases + 1 communication
        assert milestones[4]["title"] == "Inventory completed"
        assert milestones[4]["completed"] is True


def _can_import_security() -> bool:
    """Check if app.core.security can be imported (requires cryptography)."""
    try:
        from app.core.security import ROLE_PERMISSIONS  # noqa: F401
        return True
    except BaseException:
        return False


_SECURITY_AVAILABLE = _can_import_security()


class TestPortalAPIRoutes:
    """Test that portal API routes are registered correctly."""

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_portal_router_exists(self):
        from app.api.v1.portal import router
        assert router is not None

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_portal_routes_registered(self):
        from app.api.v1.portal import router
        routes = [r.path for r in router.routes]
        assert "/matters" in routes
        assert "/matters/{matter_id}/overview" in routes
        assert "/matters/{matter_id}/documents" in routes
        assert "/matters/{matter_id}/messages" in routes
        assert "/matters/{matter_id}/messages/{comm_id}/acknowledge" in routes

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_portal_included_in_api_router(self):
        from app.api.v1 import api_router
        route_paths = [r.path for r in api_router.routes]
        portal_routes = [p for p in route_paths if "/portal" in p]
        assert len(portal_routes) > 0


class TestBeneficiaryRoleRestrictions:
    """Verify that the portal service enforces beneficiary role."""

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_beneficiary_permissions_defined(self):
        from app.core.security import ROLE_PERMISSIONS
        perms = ROLE_PERMISSIONS[StakeholderRole.beneficiary]
        assert "matter:read:summary" in perms
        assert "task:read:milestones" in perms
        assert "document:read:shared" in perms
        assert "communication:read:visible" in perms

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_beneficiary_cannot_write_tasks(self):
        from app.core.security import _has_permission
        assert _has_permission(StakeholderRole.beneficiary, "task:write") is False

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_beneficiary_cannot_upload_documents(self):
        from app.core.security import _has_permission
        assert _has_permission(StakeholderRole.beneficiary, "document:upload") is False

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_beneficiary_cannot_manage_stakeholders(self):
        from app.core.security import _has_permission
        assert _has_permission(StakeholderRole.beneficiary, "stakeholder:manage") is False

    @pytest.mark.skipif(not _SECURITY_AVAILABLE, reason="cryptography not available")
    def test_beneficiary_cannot_trigger_ai(self):
        from app.core.security import _has_permission
        assert _has_permission(StakeholderRole.beneficiary, "ai:trigger") is False
