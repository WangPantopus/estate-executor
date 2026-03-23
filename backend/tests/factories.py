"""Test data factories for Estate Executor models.

Provides both class-based Factory pattern (FirmFactory, UserFactory, etc.)
and function-based helpers (make_firm, make_user, etc.) for convenience.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


# ═════════════════════════════════════════════════════════════════════════════
# Base Factory
# ═════════════════════════════════════════════════════════════════════════════


class BaseFactory:
    """Base class for test data factories."""

    DEFAULTS: dict[str, Any] = {}

    @classmethod
    def build(cls, **overrides: Any) -> dict[str, Any]:
        """Build a dict of model attributes with optional overrides."""
        data = {}
        for key, value in cls.DEFAULTS.items():
            data[key] = value() if callable(value) else value
        data.update(overrides)
        return data

    @classmethod
    def build_batch(cls, count: int, **overrides: Any) -> list[dict[str, Any]]:
        return [cls.build(**overrides) for _ in range(count)]


# ═════════════════════════════════════════════════════════════════════════════
# Model Factories
# ═════════════════════════════════════════════════════════════════════════════


class FirmFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "name": "Smith & Associates LLP",
        "slug": lambda: f"smith-associates-{uuid.uuid4().hex[:6]}",
        "type": "law_firm",
        "subscription_tier": "professional",
        "settings": dict,
        "created_at": _now,
        "updated_at": _now,
    }


class UserFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "auth_provider_id": lambda: f"auth0|{uuid.uuid4().hex[:24]}",
        "email": lambda: f"user-{uuid.uuid4().hex[:8]}@example.com",
        "full_name": "Jane Doe",
        "phone": None,
        "avatar_url": None,
        "created_at": _now,
        "updated_at": _now,
    }


class MatterFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "firm_id": _uuid,
        "title": "Estate of John Smith",
        "status": "active",
        "estate_type": "testate_probate",
        "jurisdiction_state": "CA",
        "date_of_death": lambda: date(2026, 1, 15),
        "date_of_incapacity": None,
        "decedent_name": "John Smith",
        "estimated_value": lambda: Decimal("2500000.00"),
        "phase": "immediate",
        "settings": dict,
        "created_at": _now,
        "updated_at": _now,
        "closed_at": None,
    }


class StakeholderFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "user_id": None,
        "email": lambda: f"stakeholder-{uuid.uuid4().hex[:8]}@example.com",
        "full_name": "Sarah Chen",
        "role": "matter_admin",
        "relationship_label": "estate attorney",
        "permissions": dict,
        "invite_status": "accepted",
        "invite_token": None,
        "notification_preferences": dict,
        "created_at": _now,
        "updated_at": _now,
    }


class TaskFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "parent_task_id": None,
        "template_key": None,
        "title": "Obtain Death Certificates",
        "description": "Order 10 certified copies of the death certificate.",
        "instructions": None,
        "phase": "immediate",
        "status": "not_started",
        "priority": "normal",
        "assigned_to": None,
        "due_date": lambda: date(2026, 2, 15),
        "due_date_rule": None,
        "requires_document": False,
        "completed_at": None,
        "completed_by": None,
        "sort_order": 0,
        "metadata": dict,
        "created_at": _now,
        "updated_at": _now,
    }


class AssetFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "asset_type": "bank_account",
        "title": "Chase Checking Account",
        "description": "Primary checking account",
        "institution": "JPMorgan Chase",
        "account_number_encrypted": None,
        "ownership_type": "individual",
        "transfer_mechanism": "probate",
        "status": "discovered",
        "date_of_death_value": lambda: Decimal("50000.00"),
        "current_estimated_value": lambda: Decimal("50000.00"),
        "final_appraised_value": None,
        "metadata": dict,
        "created_at": _now,
        "updated_at": _now,
    }


class EntityFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "entity_type": "revocable_trust",
        "name": "Smith Family Trust",
        "trustee": "Jane Smith",
        "successor_trustee": "First National Bank",
        "trigger_conditions": None,
        "funding_status": "fully_funded",
        "distribution_rules": None,
        "metadata": dict,
        "created_at": _now,
        "updated_at": _now,
    }


class DocumentFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "uploaded_by": _uuid,
        "filename": "death_certificate.pdf",
        "storage_key": lambda: f"firms/docs/{uuid.uuid4()}.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 245000,
        "doc_type": "death_certificate",
        "doc_type_confidence": 0.95,
        "doc_type_confirmed": False,
        "ai_extracted_data": None,
        "current_version": 1,
        "created_at": _now,
    }


class DeadlineFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "task_id": None,
        "title": "Federal Estate Tax Return (Form 706)",
        "description": "Due 9 months from date of death",
        "due_date": lambda: date(2026, 10, 15),
        "source": "auto",
        "rule": lambda: {"type": "federal_estate_tax", "base": "date_of_death", "months": 9},
        "status": "upcoming",
        "assigned_to": None,
        "reminder_config": lambda: {"days_before": [30, 7, 1]},
        "last_reminder_sent": None,
        "created_at": _now,
        "updated_at": _now,
    }


class EventFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "actor_id": _uuid,
        "actor_type": "user",
        "entity_type": "task",
        "entity_id": _uuid,
        "action": "created",
        "changes": None,
        "metadata": dict,
        "ip_address": None,
        "user_agent": None,
        "created_at": _now,
    }


class CommunicationFactory(BaseFactory):
    DEFAULTS = {
        "id": _uuid,
        "matter_id": _uuid,
        "sender_id": _uuid,
        "type": "message",
        "subject": "Status update",
        "body": "Everything is proceeding as planned.",
        "visibility": "all_stakeholders",
        "visible_to": None,
        "acknowledged_by": None,
        "created_at": _now,
    }


class CurrentUserFactory(BaseFactory):
    DEFAULTS = {
        "user_id": _uuid,
        "email": lambda: f"user-{uuid.uuid4().hex[:8]}@example.com",
        "firm_memberships": list,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Convenience function aliases
# ═════════════════════════════════════════════════════════════════════════════

make_firm = FirmFactory.build
make_user = UserFactory.build
make_matter = MatterFactory.build
make_stakeholder = StakeholderFactory.build
make_task = TaskFactory.build
make_asset = AssetFactory.build
make_entity = EntityFactory.build
make_document = DocumentFactory.build
make_deadline = DeadlineFactory.build
make_event = EventFactory.build
make_communication = CommunicationFactory.build
make_current_user = CurrentUserFactory.build
