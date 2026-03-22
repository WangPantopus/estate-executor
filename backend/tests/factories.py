"""Test data factories for Estate Executor models.

Uses factory_boy patterns but implemented as simple dataclass-like builders
to avoid tight coupling to SQLAlchemy session (tests mock the DB layer).
Each factory returns a dict that can be used as kwargs or unpacked into models.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Firm ─────────────────────────────────────────────────────────────────────


def make_firm(**overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "name": "Smith & Associates LLP",
        "slug": f"smith-associates-{uuid.uuid4().hex[:6]}",
        "type": "law_firm",
        "subscription_tier": "professional",
        "settings": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── User ─────────────────────────────────────────────────────────────────────


def make_user(**overrides: Any) -> dict[str, Any]:
    uid = _uuid()
    defaults = {
        "id": uid,
        "auth_provider_id": f"auth0|{uid.hex[:24]}",
        "email": f"user-{uid.hex[:8]}@example.com",
        "full_name": "Jane Doe",
        "phone": None,
        "avatar_url": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Matter ───────────────────────────────────────────────────────────────────


def make_matter(firm_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "firm_id": firm_id or _uuid(),
        "title": "Estate of John Smith",
        "status": "active",
        "estate_type": "testate_probate",
        "jurisdiction_state": "CA",
        "date_of_death": date(2026, 1, 15),
        "date_of_incapacity": None,
        "decedent_name": "John Smith",
        "estimated_value": Decimal("2500000.00"),
        "phase": "immediate",
        "settings": {},
        "created_at": _now(),
        "updated_at": _now(),
        "closed_at": None,
    }
    defaults.update(overrides)
    return defaults


# ─── Stakeholder ──────────────────────────────────────────────────────────────


def make_stakeholder(
    matter_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "matter_id": matter_id or _uuid(),
        "user_id": user_id,
        "email": f"stakeholder-{uuid.uuid4().hex[:8]}@example.com",
        "full_name": "Sarah Chen",
        "role": "matter_admin",
        "relationship_label": "estate attorney",
        "permissions": {},
        "invite_status": "accepted",
        "invite_token": None,
        "notification_preferences": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Task ─────────────────────────────────────────────────────────────────────


def make_task(matter_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "matter_id": matter_id or _uuid(),
        "parent_task_id": None,
        "template_key": None,
        "title": "Obtain Death Certificates",
        "description": "Order 10 certified copies of the death certificate.",
        "instructions": None,
        "phase": "immediate",
        "status": "not_started",
        "priority": "normal",
        "assigned_to": None,
        "due_date": date(2026, 2, 15),
        "due_date_rule": None,
        "requires_document": False,
        "completed_at": None,
        "completed_by": None,
        "sort_order": 0,
        "metadata": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Asset ────────────────────────────────────────────────────────────────────


def make_asset(matter_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "matter_id": matter_id or _uuid(),
        "asset_type": "bank_account",
        "title": "Chase Checking Account",
        "description": "Primary checking account",
        "institution": "JPMorgan Chase",
        "account_number_encrypted": None,
        "ownership_type": "individual",
        "transfer_mechanism": "probate",
        "status": "discovered",
        "date_of_death_value": Decimal("50000.00"),
        "current_estimated_value": Decimal("50000.00"),
        "final_appraised_value": None,
        "metadata": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Entity ───────────────────────────────────────────────────────────────────


def make_entity(matter_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "matter_id": matter_id or _uuid(),
        "entity_type": "revocable_trust",
        "name": "Smith Family Trust",
        "trustee": "Jane Smith",
        "successor_trustee": "First National Bank",
        "trigger_conditions": None,
        "funding_status": "fully_funded",
        "distribution_rules": None,
        "metadata": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Document ─────────────────────────────────────────────────────────────────


def make_document(matter_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    doc_id = overrides.get("id", _uuid())
    defaults = {
        "id": doc_id,
        "matter_id": matter_id or _uuid(),
        "uploaded_by": _uuid(),
        "filename": "death_certificate.pdf",
        "storage_key": f"firms/docs/{doc_id}.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 245000,
        "doc_type": "death_certificate",
        "doc_type_confidence": 0.95,
        "doc_type_confirmed": False,
        "ai_extracted_data": None,
        "current_version": 1,
        "created_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Deadline ─────────────────────────────────────────────────────────────────


def make_deadline(matter_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "matter_id": matter_id or _uuid(),
        "task_id": None,
        "title": "Federal Estate Tax Return (Form 706)",
        "description": "Due 9 months from date of death",
        "due_date": date(2026, 10, 15),
        "source": "auto",
        "rule": {"type": "federal_estate_tax", "base": "date_of_death", "months": 9},
        "status": "upcoming",
        "assigned_to": None,
        "reminder_config": {"days_before": [30, 7, 1]},
        "last_reminder_sent": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Event ────────────────────────────────────────────────────────────────────


def make_event(matter_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "matter_id": matter_id or _uuid(),
        "actor_id": _uuid(),
        "actor_type": "user",
        "entity_type": "task",
        "entity_id": _uuid(),
        "action": "created",
        "changes": None,
        "metadata": {},
        "ip_address": None,
        "user_agent": None,
        "created_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── Communication ────────────────────────────────────────────────────────────


def make_communication(matter_id: uuid.UUID | None = None, **overrides: Any) -> dict[str, Any]:
    defaults = {
        "id": _uuid(),
        "matter_id": matter_id or _uuid(),
        "sender_id": _uuid(),
        "type": "message",
        "subject": "Status update",
        "body": "Everything is proceeding as planned.",
        "visibility": "all_stakeholders",
        "visible_to": None,
        "acknowledged_by": None,
        "created_at": _now(),
    }
    defaults.update(overrides)
    return defaults


# ─── CurrentUser (schema, not model) ─────────────────────────────────────────


def make_current_user(**overrides: Any) -> dict[str, Any]:
    uid = overrides.get("user_id", _uuid())
    defaults = {
        "user_id": uid,
        "email": f"user-{str(uid)[:8]}@example.com",
        "firm_memberships": [],
    }
    defaults.update(overrides)
    return defaults
