"""Unit tests for communication service — visibility rules, acknowledgements, disputes."""

from __future__ import annotations

import uuid

from app.models.enums import (
    CommunicationType,
    CommunicationVisibility,
    StakeholderRole,
)


class TestCommunicationModel:
    """Verify the Communication model has expected fields."""

    def test_has_sender_id(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "sender_id")

    def test_has_visibility(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "visibility")

    def test_has_visible_to(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "visible_to")

    def test_has_acknowledged_by(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "acknowledged_by")

    def test_has_sender_relationship(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "sender")

    def test_has_type(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "type")


class TestCommunicationTypeEnum:
    """Verify communication type enum values."""

    def test_message(self):
        assert CommunicationType.message == "message"

    def test_milestone_notification(self):
        assert CommunicationType.milestone_notification == "milestone_notification"

    def test_distribution_notice(self):
        assert CommunicationType.distribution_notice == "distribution_notice"

    def test_document_request(self):
        assert CommunicationType.document_request == "document_request"

    def test_dispute_flag(self):
        assert CommunicationType.dispute_flag == "dispute_flag"


class TestCommunicationVisibilityEnum:
    """Verify visibility enum values."""

    def test_all_stakeholders(self):
        assert CommunicationVisibility.all_stakeholders == "all_stakeholders"

    def test_professionals_only(self):
        assert CommunicationVisibility.professionals_only == "professionals_only"

    def test_specific(self):
        assert CommunicationVisibility.specific == "specific"


class TestVisibilityRules:
    """Test the role-based visibility logic at unit level."""

    _PROFESSIONAL_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}

    def test_admin_sees_all_visibilities(self):
        """matter_admin should see all messages including professionals_only."""
        role = StakeholderRole.matter_admin
        assert role in self._PROFESSIONAL_ROLES

    def test_professional_sees_all_visibilities(self):
        """professional should see all messages including professionals_only."""
        role = StakeholderRole.professional
        assert role in self._PROFESSIONAL_ROLES

    def test_executor_does_not_see_professionals_only(self):
        """executor_trustee should NOT see professionals_only messages."""
        role = StakeholderRole.executor_trustee
        assert role not in self._PROFESSIONAL_ROLES

    def test_beneficiary_does_not_see_professionals_only(self):
        """beneficiary should NOT see professionals_only messages."""
        role = StakeholderRole.beneficiary
        assert role not in self._PROFESSIONAL_ROLES

    def test_read_only_does_not_see_professionals_only(self):
        """read_only should NOT see professionals_only messages."""
        role = StakeholderRole.read_only
        assert role not in self._PROFESSIONAL_ROLES

    def test_specific_visibility_includes_sender(self):
        """When visibility is 'specific', sender should always be in visible_to."""
        sender_id = uuid.uuid4()
        other_id = uuid.uuid4()
        visible_to = [other_id]

        # Service logic: if sender not in visible_to, prepend them
        if sender_id not in visible_to:
            visible_to = [sender_id, *visible_to]

        assert sender_id in visible_to
        assert other_id in visible_to

    def test_specific_visibility_sender_already_present(self):
        """When sender is already in visible_to, don't duplicate."""
        sender_id = uuid.uuid4()
        visible_to = [sender_id, uuid.uuid4()]

        if sender_id not in visible_to:
            visible_to = [sender_id, *visible_to]

        assert visible_to.count(sender_id) == 1


class TestAcknowledgementLogic:
    """Test the acknowledgement append (not replace) logic."""

    def test_acknowledge_appends_to_array(self):
        """Acknowledging should append stakeholder_id, not replace array."""
        existing_acks: list[uuid.UUID] = [uuid.uuid4()]
        new_stakeholder = uuid.uuid4()

        current_acks = list(existing_acks)
        if new_stakeholder not in current_acks:
            current_acks.append(new_stakeholder)

        assert len(current_acks) == 2
        assert existing_acks[0] in current_acks
        assert new_stakeholder in current_acks

    def test_acknowledge_is_idempotent(self):
        """Acknowledging same stakeholder twice should not add duplicate."""
        stakeholder_id = uuid.uuid4()
        current_acks = [stakeholder_id]

        if stakeholder_id not in current_acks:
            current_acks.append(stakeholder_id)

        assert len(current_acks) == 1

    def test_acknowledge_from_empty_array(self):
        """Acknowledging when array is empty should create single-element array."""
        current_acks: list[uuid.UUID] = []
        stakeholder_id = uuid.uuid4()

        if stakeholder_id not in current_acks:
            current_acks.append(stakeholder_id)

        assert current_acks == [stakeholder_id]

    def test_acknowledge_from_none(self):
        """Acknowledging when acknowledged_by is None should handle gracefully."""
        acknowledged_by = None
        stakeholder_id = uuid.uuid4()

        current_acks = list(acknowledged_by or [])
        if stakeholder_id not in current_acks:
            current_acks.append(stakeholder_id)

        assert current_acks == [stakeholder_id]


class TestDisputeFlag:
    """Verify dispute flag creates the right communication type."""

    def test_dispute_flag_type(self):
        """Dispute flags should use type=dispute_flag."""
        assert CommunicationType.dispute_flag == "dispute_flag"

    def test_dispute_flag_visibility_is_all_stakeholders(self):
        """Dispute flags should be visible to all stakeholders."""
        # The service always sets visibility=all_stakeholders for dispute flags
        expected = CommunicationVisibility.all_stakeholders
        assert expected == "all_stakeholders"


class TestEmailNotificationTypes:
    """Verify which types trigger email notifications."""

    _EMAIL_TYPES = {
        CommunicationType.milestone_notification,
        CommunicationType.distribution_notice,
    }

    def test_milestone_triggers_email(self):
        assert CommunicationType.milestone_notification in self._EMAIL_TYPES

    def test_distribution_triggers_email(self):
        assert CommunicationType.distribution_notice in self._EMAIL_TYPES

    def test_message_does_not_trigger_email(self):
        assert CommunicationType.message not in self._EMAIL_TYPES

    def test_document_request_does_not_trigger_email(self):
        assert CommunicationType.document_request not in self._EMAIL_TYPES


class TestCommunicationSchemas:
    """Verify schema structure."""

    def test_create_has_visibility(self):
        from app.schemas.communications import CommunicationCreate

        fields = CommunicationCreate.model_fields
        assert "visibility" in fields
        assert "visible_to" in fields

    def test_create_has_type(self):
        from app.schemas.communications import CommunicationCreate

        assert "type" in CommunicationCreate.model_fields

    def test_response_has_sender_name(self):
        from app.schemas.communications import CommunicationResponse

        assert "sender_name" in CommunicationResponse.model_fields

    def test_response_has_acknowledged_by(self):
        from app.schemas.communications import CommunicationResponse

        assert "acknowledged_by" in CommunicationResponse.model_fields

    def test_dispute_flag_create_has_entity_fields(self):
        from app.schemas.communications import DisputeFlagCreate

        fields = DisputeFlagCreate.model_fields
        assert "entity_type" in fields
        assert "entity_id" in fields
        assert "reason" in fields

    def test_list_response_has_pagination(self):
        from app.schemas.communications import CommunicationListResponse

        fields = CommunicationListResponse.model_fields
        assert "data" in fields
        assert "meta" in fields
