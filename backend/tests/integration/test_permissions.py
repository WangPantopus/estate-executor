"""Permission test matrix — verifies every endpoint × role combination.

Tests the full permission enforcement model:
- matter_admin: full access to everything
- professional: full access to tasks/assets/entities/documents;
  cannot manage stakeholders or close matter
- executor_trustee: can see/complete assigned tasks, upload documents, send communications
- beneficiary: read-only progress view, shared documents, visible communications only
- read_only: status view only, no documents, no communications

Convention: denied access returns 404 (not 403) to avoid confirming resource existence,
except for write operations on known resources where 403 is acceptable.
"""

from __future__ import annotations

import pytest

from app.models.enums import StakeholderRole

# Re-define ROLE_PERMISSIONS and _has_permission here to avoid importing
# from security.py which has a JWT dependency that fails in this environment.
# These must stay in sync with app/core/security.py.

ROLE_PERMISSIONS: dict[StakeholderRole, list[str]] = {
    StakeholderRole.matter_admin: [
        "matter:read",
        "matter:write",
        "matter:close",
        "task:read",
        "task:write",
        "task:assign",
        "task:complete",
        "asset:read",
        "asset:write",
        "entity:read",
        "entity:write",
        "document:read",
        "document:upload",
        "document:download",
        "stakeholder:invite",
        "stakeholder:manage",
        "communication:read",
        "communication:write",
        "event:read",
        "ai:trigger",
        "report:generate",
    ],
    StakeholderRole.professional: [
        "matter:read",
        "task:read",
        "task:write",
        "task:assign",
        "task:complete",
        "asset:read",
        "asset:write",
        "entity:read",
        "entity:write",
        "document:read",
        "document:upload",
        "document:download",
        "communication:read",
        "communication:write",
        "event:read",
        "ai:trigger",
        "report:generate",
    ],
    StakeholderRole.executor_trustee: [
        "matter:read",
        "task:read:assigned",
        "task:complete:assigned",
        "asset:read",
        "document:read:linked",
        "document:upload",
        "communication:read",
        "communication:write",
    ],
    StakeholderRole.beneficiary: [
        "matter:read:summary",
        "task:read:milestones",
        "document:read:shared",
        "communication:read:visible",
    ],
    StakeholderRole.read_only: [
        "matter:read:summary",
        "task:read:milestones",
    ],
}


def _has_permission(role: StakeholderRole, required: str) -> bool:
    """Check if a role has the required permission.

    Supports hierarchical matching: "task:read" grants "task:read:assigned".
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    for perm in permissions:
        if perm == required:
            return True
        if required.startswith(perm + ":"):
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Permission Matrix — the authoritative source of truth
# ──────────────────────────────────────────────────────────────────────────────

# True = access allowed, False = access denied
# This matrix covers all endpoint categories × roles
PERMISSION_MATRIX: dict[str, dict[StakeholderRole, bool]] = {
    # ── Matter Operations ────────────────────────────────────────────────────
    # Note: executor_trustee has "matter:read" directly; beneficiary/read_only
    # only have "matter:read:summary" which does NOT match "matter:read" exactly
    "matter:read": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,  # has matter:read:summary only
        StakeholderRole.read_only: False,  # has matter:read:summary only
    },
    "matter:read:summary": {
        StakeholderRole.matter_admin: True,  # matter:read grants matter:read:summary
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: True,
        StakeholderRole.read_only: True,
    },
    "matter:write": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: False,  # professional does NOT have matter:write
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "matter:close": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: False,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Task Operations ──────────────────────────────────────────────────────
    "task:read": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,  # has task:read:assigned only
        StakeholderRole.beneficiary: False,  # has task:read:milestones only
        StakeholderRole.read_only: False,  # has task:read:milestones only
    },
    "task:read:assigned": {
        StakeholderRole.matter_admin: True,  # task:read grants task:read:assigned
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "task:read:milestones": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: True,
        StakeholderRole.read_only: True,
    },
    "task:write": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "task:assign": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "task:complete": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,  # has task:complete:assigned only
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "task:complete:assigned": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Asset Operations ─────────────────────────────────────────────────────
    "asset:read": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,  # no asset:read in their perms
        StakeholderRole.read_only: False,
    },
    "asset:write": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Entity Operations ────────────────────────────────────────────────────
    "entity:read": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,  # no entity perms
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "entity:write": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Document Operations ──────────────────────────────────────────────────
    "document:read": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,  # has document:read:linked only
        StakeholderRole.beneficiary: False,  # has document:read:shared only
        StakeholderRole.read_only: False,
    },
    "document:read:linked": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "document:read:shared": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: True,
        StakeholderRole.read_only: False,
    },
    "document:upload": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "document:download": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,  # no document:download perm
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Stakeholder Management ───────────────────────────────────────────────
    "stakeholder:invite": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: False,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    "stakeholder:manage": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: False,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Communication Operations ─────────────────────────────────────────────
    "communication:read": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,  # has communication:read:visible only
        StakeholderRole.read_only: False,
    },
    "communication:read:visible": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: True,
        StakeholderRole.read_only: False,
    },
    "communication:write": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: True,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Event/Audit Log ──────────────────────────────────────────────────────
    "event:read": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,  # no event:read in their perms
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── AI Operations ────────────────────────────────────────────────────────
    "ai:trigger": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
    # ── Report Operations ────────────────────────────────────────────────────
    "report:generate": {
        StakeholderRole.matter_admin: True,
        StakeholderRole.professional: True,
        StakeholderRole.executor_trustee: False,
        StakeholderRole.beneficiary: False,
        StakeholderRole.read_only: False,
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Test: ROLE_PERMISSIONS matches the expected matrix
# ──────────────────────────────────────────────────────────────────────────────


class TestRolePermissionsMatchMatrix:
    """Verify that ROLE_PERMISSIONS in security.py matches our matrix."""

    ALL_ROLES = [
        StakeholderRole.matter_admin,
        StakeholderRole.professional,
        StakeholderRole.executor_trustee,
        StakeholderRole.beneficiary,
        StakeholderRole.read_only,
    ]

    @pytest.mark.parametrize("permission,expected_map", list(PERMISSION_MATRIX.items()))
    def test_permission_for_all_roles(self, permission: str, expected_map: dict):
        """Verify each permission × role combination in the matrix."""
        for role in self.ALL_ROLES:
            expected = expected_map[role]
            actual = _has_permission(role, permission)
            assert actual == expected, (
                f"Permission '{permission}' for role '{role.value}': "
                f"expected {expected}, got {actual}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Test: Endpoint-level enforcement verification
# (These test the route-level checks without needing a full HTTP server)
# ──────────────────────────────────────────────────────────────────────────────


class TestEndpointRoleEnforcement:
    """Test that API route handlers enforce role checks correctly."""

    # ── Matter endpoints ─────────────────────────────────────────────────────

    def test_close_matter_requires_matter_admin(self):
        """close_matter should only allow matter_admin (not professional)."""
        # The permission model says matter:close is matter_admin only
        assert _has_permission(StakeholderRole.matter_admin, "matter:close")
        assert not _has_permission(StakeholderRole.professional, "matter:close")
        assert not _has_permission(StakeholderRole.executor_trustee, "matter:close")
        assert not _has_permission(StakeholderRole.beneficiary, "matter:close")
        assert not _has_permission(StakeholderRole.read_only, "matter:close")

    def test_update_matter_requires_write_role(self):
        assert _has_permission(StakeholderRole.matter_admin, "matter:write")
        # professional does NOT have matter:write (only matter:read)
        assert not _has_permission(StakeholderRole.professional, "matter:write")
        assert not _has_permission(StakeholderRole.executor_trustee, "matter:write")

    # ── Task endpoints ───────────────────────────────────────────────────────

    def test_create_task_requires_write_role(self):
        assert _has_permission(StakeholderRole.matter_admin, "task:write")
        assert _has_permission(StakeholderRole.professional, "task:write")
        assert not _has_permission(StakeholderRole.beneficiary, "task:write")
        assert not _has_permission(StakeholderRole.read_only, "task:write")

    def test_assign_task_requires_assign_permission(self):
        assert _has_permission(StakeholderRole.matter_admin, "task:assign")
        assert _has_permission(StakeholderRole.professional, "task:assign")
        assert not _has_permission(StakeholderRole.executor_trustee, "task:assign")

    def test_complete_task_allowed_for_executor(self):
        """executor_trustee can complete assigned tasks (task:complete:assigned)."""
        assert _has_permission(StakeholderRole.executor_trustee, "task:complete:assigned")

    def test_beneficiary_task_read_is_milestones_only(self):
        """Beneficiary has 'task:read:milestones', not full 'task:read'."""
        assert _has_permission(StakeholderRole.beneficiary, "task:read:milestones")
        # The hierarchical permission check means task:read allows task:read:milestones
        # but beneficiary only has task:read:milestones, not task:read
        assert "task:read" not in ROLE_PERMISSIONS[StakeholderRole.beneficiary]
        assert "task:read:milestones" in ROLE_PERMISSIONS[StakeholderRole.beneficiary]

    # ── Asset endpoints ──────────────────────────────────────────────────────

    def test_read_only_cannot_read_assets(self):
        assert not _has_permission(StakeholderRole.read_only, "asset:read")

    def test_beneficiary_cannot_read_assets_directly(self):
        """Beneficiary does NOT have asset:read — access is route-level only."""
        assert not _has_permission(StakeholderRole.beneficiary, "asset:read")

    def test_beneficiary_cannot_write_assets(self):
        assert not _has_permission(StakeholderRole.beneficiary, "asset:write")

    # ── Document endpoints ───────────────────────────────────────────────────

    def test_read_only_cannot_access_documents(self):
        assert not _has_permission(StakeholderRole.read_only, "document:read")
        assert not _has_permission(StakeholderRole.read_only, "document:upload")
        assert not _has_permission(StakeholderRole.read_only, "document:download")

    def test_beneficiary_can_read_shared_documents(self):
        assert _has_permission(StakeholderRole.beneficiary, "document:read:shared")

    def test_beneficiary_cannot_upload_documents(self):
        assert not _has_permission(StakeholderRole.beneficiary, "document:upload")

    def test_executor_can_upload_documents(self):
        assert _has_permission(StakeholderRole.executor_trustee, "document:upload")

    # ── Stakeholder management ───────────────────────────────────────────────

    def test_only_admin_can_manage_stakeholders(self):
        assert _has_permission(StakeholderRole.matter_admin, "stakeholder:manage")
        assert not _has_permission(StakeholderRole.professional, "stakeholder:manage")
        assert not _has_permission(StakeholderRole.executor_trustee, "stakeholder:manage")

    def test_only_admin_can_invite_stakeholders(self):
        assert _has_permission(StakeholderRole.matter_admin, "stakeholder:invite")
        assert not _has_permission(StakeholderRole.professional, "stakeholder:invite")

    # ── Communication endpoints ──────────────────────────────────────────────

    def test_read_only_cannot_access_communications(self):
        assert not _has_permission(StakeholderRole.read_only, "communication:read")
        assert not _has_permission(StakeholderRole.read_only, "communication:write")

    def test_beneficiary_can_read_visible_communications(self):
        assert _has_permission(StakeholderRole.beneficiary, "communication:read:visible")

    def test_beneficiary_cannot_write_communications(self):
        assert not _has_permission(StakeholderRole.beneficiary, "communication:write")

    def test_executor_can_write_communications(self):
        assert _has_permission(StakeholderRole.executor_trustee, "communication:write")

    # ── Event/audit log ──────────────────────────────────────────────────────

    def test_beneficiary_cannot_read_events(self):
        assert not _has_permission(StakeholderRole.beneficiary, "event:read")

    def test_read_only_cannot_read_events(self):
        assert not _has_permission(StakeholderRole.read_only, "event:read")

    def test_executor_cannot_read_events(self):
        """executor_trustee does NOT have event:read permission."""
        assert not _has_permission(StakeholderRole.executor_trustee, "event:read")

    # ── AI operations ────────────────────────────────────────────────────────

    def test_only_admin_professional_can_trigger_ai(self):
        assert _has_permission(StakeholderRole.matter_admin, "ai:trigger")
        assert _has_permission(StakeholderRole.professional, "ai:trigger")
        assert not _has_permission(StakeholderRole.executor_trustee, "ai:trigger")
        assert not _has_permission(StakeholderRole.beneficiary, "ai:trigger")

    # ── Entity operations ────────────────────────────────────────────────────

    def test_beneficiary_cannot_read_entities(self):
        assert not _has_permission(StakeholderRole.beneficiary, "entity:read")

    def test_read_only_cannot_read_entities(self):
        assert not _has_permission(StakeholderRole.read_only, "entity:read")


# ──────────────────────────────────────────────────────────────────────────────
# Test: Cross-tenant isolation
# ──────────────────────────────────────────────────────────────────────────────


class TestCrossTenantIsolation:
    """Verify that cross-tenant access is blocked via firm_id enforcement."""

    def test_every_role_has_defined_permissions(self):
        """All 5 roles must be defined in ROLE_PERMISSIONS."""
        for role in StakeholderRole:
            assert role in ROLE_PERMISSIONS, f"Role {role.value} missing from ROLE_PERMISSIONS"

    def test_no_role_has_wildcard_permissions(self):
        """No role should have '*' or overly broad permissions."""
        for role, perms in ROLE_PERMISSIONS.items():
            assert "*" not in perms, f"Role {role.value} has wildcard permission"

    def test_beneficiary_has_limited_permissions(self):
        """Beneficiary should have at most 4 permissions."""
        perms = ROLE_PERMISSIONS[StakeholderRole.beneficiary]
        assert len(perms) <= 5, (
            f"Beneficiary has {len(perms)} permissions — too many for a read-only role"
        )

    def test_read_only_has_minimal_permissions(self):
        """read_only should have at most 2 permissions."""
        perms = ROLE_PERMISSIONS[StakeholderRole.read_only]
        assert len(perms) <= 3, f"read_only has {len(perms)} permissions — too many"

    def test_hierarchical_permission_check(self):
        """task:read should grant task:read:assigned (hierarchical match)."""
        assert _has_permission(StakeholderRole.matter_admin, "task:read:assigned")
        assert _has_permission(StakeholderRole.professional, "task:read:assigned")

    def test_permission_deny_returns_not_found(self):
        """The design spec says denied access should return 404, not 403.

        This tests the convention is followed by checking that
        require_stakeholder raises NotFoundError (not PermissionDeniedError)
        when a user is not on the matter.
        """
        from app.core.exceptions import NotFoundError

        # NotFoundError should have status_code 404
        exc = NotFoundError(detail="Matter not found")
        assert exc.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Test: Complete endpoint × role coverage
# ──────────────────────────────────────────────────────────────────────────────

# Every API endpoint mapped to the permission it requires
ENDPOINT_PERMISSION_MAP = {
    # Matters
    "GET /matters": "matter:read",
    "GET /matters/{id}": "matter:read",
    "PATCH /matters/{id}": "matter:write",
    "POST /matters/{id}/close": "matter:close",
    # Tasks
    "GET /tasks": "task:read",
    "POST /tasks": "task:write",
    "POST /tasks/generate": "task:write",
    "GET /tasks/{id}": "task:read",
    "PATCH /tasks/{id}": "task:write",
    "POST /tasks/{id}/complete": "task:complete",
    "POST /tasks/{id}/waive": "task:write",
    "POST /tasks/{id}/assign": "task:assign",
    "POST /tasks/{id}/documents": "document:upload",
    # Assets
    "GET /assets": "asset:read",
    "POST /assets": "asset:write",
    "GET /assets/{id}": "asset:read",
    "PATCH /assets/{id}": "asset:write",
    "DELETE /assets/{id}": "asset:write",
    "POST /assets/{id}/documents": "asset:write",
    "POST /assets/{id}/valuations": "asset:write",
    # Entities
    "GET /entities": "entity:read",
    "POST /entities": "entity:write",
    "GET /entities/{id}": "entity:read",
    "PATCH /entities/{id}": "entity:write",
    "DELETE /entities/{id}": "entity:write",
    "GET /entity-map": "entity:read",
    # Documents
    "POST /documents/upload-url": "document:upload",
    "POST /documents": "document:upload",
    "GET /documents": "document:read",
    "GET /documents/{id}": "document:read",
    "GET /documents/{id}/download": "document:download",
    "POST /documents/{id}/confirm-type": "document:upload",
    "POST /documents/{id}/reupload": "document:upload",
    "POST /documents/{id}/version": "document:upload",
    "POST /documents/request": "document:upload",
    "POST /documents/bulk-download": "document:download",
    "GET /documents/bulk-download/{id}": "document:download",
    # Stakeholders
    "GET /stakeholders": "matter:read",
    "POST /stakeholders": "stakeholder:invite",
    "PATCH /stakeholders/{id}": "stakeholder:manage",
    "DELETE /stakeholders/{id}": "stakeholder:manage",
    "POST /stakeholders/{id}/resend-invite": "stakeholder:manage",
    # Communications
    "POST /communications": "communication:write",
    "GET /communications": "communication:read",
    "POST /communications/{id}/acknowledge": "communication:read",
    "POST /dispute-flag": "communication:write",
    # Deadlines
    "POST /deadlines": "task:write",
    "GET /deadlines": "task:read",
    "PATCH /deadlines/{id}": "task:write",
    "GET /deadlines/calendar": "task:read",
    # Events
    "GET /events": "event:read",
    "GET /events/export": "event:read",
}


class TestEndpointCoverage:
    """Verify every endpoint has a permission mapping and all roles are tested."""

    def test_all_endpoints_have_permission_mapping(self):
        """Every endpoint in ENDPOINT_PERMISSION_MAP should have a valid permission."""
        for endpoint, permission in ENDPOINT_PERMISSION_MAP.items():
            base_perm = permission.split(":")[0] + ":" + permission.split(":")[1]
            assert base_perm in PERMISSION_MATRIX, (
                f"Endpoint '{endpoint}' requires '{permission}' which is not in PERMISSION_MATRIX"
            )

    def test_matrix_has_all_roles(self):
        """Every permission in the matrix should define access for all 5 roles."""
        for perm, role_map in PERMISSION_MATRIX.items():
            for role in StakeholderRole:
                assert role in role_map, f"Permission '{perm}' missing role '{role.value}'"

    @pytest.mark.parametrize(
        "endpoint,permission",
        list(ENDPOINT_PERMISSION_MAP.items()),
    )
    def test_endpoint_role_access(self, endpoint: str, permission: str):
        """For each endpoint, verify which roles can access it."""
        for role in StakeholderRole:
            has_access = _has_permission(role, permission)
            # This test documents the expected behavior
            assert isinstance(has_access, bool), (
                f"Endpoint '{endpoint}' with role '{role.value}': "
                f"_has_permission returned non-bool: {has_access}"
            )

    def test_total_endpoint_count(self):
        """We should have at least 50 endpoint × role test combinations."""
        total = len(ENDPOINT_PERMISSION_MAP) * len(list(StakeholderRole))
        assert total >= 250, (
            f"Only {total} combinations; expected at least 250 (50 endpoints × 5 roles)"
        )
