"""Unit tests for milestone detection and auto-notification."""

from __future__ import annotations  # noqa: I001

from app.models.enums import TaskPhase, TaskStatus
from app.services.milestone_service import (
    MILESTONE_DEFINITIONS,
    _PHASE_TO_MILESTONE,
    _TERMINAL_STATES,
    get_milestone_definition,
)


class TestMilestoneDefinitions:
    """Verify milestone definitions are correctly configured."""

    def test_has_five_milestones(self):
        assert len(MILESTONE_DEFINITIONS) == 5

    def test_all_have_required_keys(self):
        for m in MILESTONE_DEFINITIONS:
            assert "key" in m
            assert "title" in m
            assert "description" in m
            assert "phase" in m

    def test_keys_are_unique(self):
        keys = [m["key"] for m in MILESTONE_DEFINITIONS]
        assert len(keys) == len(set(keys))

    def test_immediate_tasks_complete(self):
        defn = get_milestone_definition("immediate_tasks_complete")
        assert defn is not None
        assert defn["phase"] == TaskPhase.immediate
        assert "Immediate" in defn["title"]

    def test_inventory_complete(self):
        defn = get_milestone_definition("inventory_complete")
        assert defn is not None
        assert defn["phase"] == TaskPhase.asset_inventory

    def test_probate_filed(self):
        defn = get_milestone_definition("probate_filed")
        assert defn is not None
        assert defn["phase"] == TaskPhase.probate_filing

    def test_tax_returns_filed(self):
        defn = get_milestone_definition("tax_returns_filed")
        assert defn is not None
        assert defn["phase"] == TaskPhase.tax

    def test_distribution_approved(self):
        defn = get_milestone_definition("distribution_approved")
        assert defn is not None
        assert defn["phase"] == TaskPhase.transfer_distribution

    def test_unknown_milestone_returns_none(self):
        assert get_milestone_definition("nonexistent") is None


class TestPhaseToMilestoneMapping:
    """Verify phase → milestone key mapping."""

    def test_immediate_phase_maps(self):
        assert _PHASE_TO_MILESTONE[TaskPhase.immediate] == "immediate_tasks_complete"

    def test_asset_inventory_maps(self):
        assert _PHASE_TO_MILESTONE[TaskPhase.asset_inventory] == "inventory_complete"

    def test_probate_filing_maps(self):
        assert _PHASE_TO_MILESTONE[TaskPhase.probate_filing] == "probate_filed"

    def test_tax_maps(self):
        assert _PHASE_TO_MILESTONE[TaskPhase.tax] == "tax_returns_filed"

    def test_transfer_distribution_maps(self):
        assert _PHASE_TO_MILESTONE[TaskPhase.transfer_distribution] == "distribution_approved"

    def test_notification_phase_has_no_milestone(self):
        assert TaskPhase.notification not in _PHASE_TO_MILESTONE

    def test_custom_phase_has_no_milestone(self):
        assert TaskPhase.custom not in _PHASE_TO_MILESTONE

    def test_family_communication_has_no_milestone(self):
        assert TaskPhase.family_communication not in _PHASE_TO_MILESTONE


class TestTerminalStates:
    """Verify terminal task states for milestone detection."""

    def test_complete_is_terminal(self):
        assert TaskStatus.complete in _TERMINAL_STATES

    def test_waived_is_terminal(self):
        assert TaskStatus.waived in _TERMINAL_STATES

    def test_cancelled_is_terminal(self):
        assert TaskStatus.cancelled in _TERMINAL_STATES

    def test_not_started_is_not_terminal(self):
        assert TaskStatus.not_started not in _TERMINAL_STATES

    def test_in_progress_is_not_terminal(self):
        assert TaskStatus.in_progress not in _TERMINAL_STATES

    def test_blocked_is_not_terminal(self):
        assert TaskStatus.blocked not in _TERMINAL_STATES


class TestMilestoneServiceIntegration:
    """Verify service functions exist and have correct signatures."""

    def test_check_phase_milestone_exists(self):
        import inspect

        from app.services.milestone_service import check_phase_milestone

        sig = inspect.signature(check_phase_milestone)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params
        assert "phase" in params

    def test_fire_milestone_notification_exists(self):
        import inspect

        from app.services.milestone_service import fire_milestone_notification

        sig = inspect.signature(fire_milestone_notification)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params
        assert "milestone_key" in params

    def test_detect_milestones_after_completion_exists(self):
        import inspect

        from app.services.milestone_service import detect_milestones_after_completion

        sig = inspect.signature(detect_milestones_after_completion)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params
        assert "completed_task_phase" in params

    def test_get_milestone_status_exists(self):
        import inspect

        from app.services.milestone_service import get_milestone_status

        sig = inspect.signature(get_milestone_status)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params

    def test_update_milestone_settings_exists(self):
        import inspect

        from app.services.milestone_service import update_milestone_settings

        sig = inspect.signature(update_milestone_settings)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params
        assert "milestone_key" in params
        assert "enabled" in params


class TestMilestoneAutoDetectionHook:
    """Verify that milestone detection is wired into task completion."""

    def test_complete_task_calls_milestone_detection(self):
        import inspect

        from app.services.task_service import complete_task

        source = inspect.getsource(complete_task)
        assert "detect_milestones_after_completion" in source
        assert "completed_task_phase=task.phase" in source

    def test_milestone_notification_creates_communication(self):
        """Verify fire_milestone_notification creates a Communication record."""
        import inspect

        from app.services.milestone_service import fire_milestone_notification

        source = inspect.getsource(fire_milestone_notification)
        assert "CommunicationType.milestone_notification" in source
        assert "db.add(comm)" in source

    def test_milestone_checks_settings(self):
        """Verify milestone respects auto_notify settings."""
        import inspect

        from app.services.milestone_service import fire_milestone_notification

        source = inspect.getsource(fire_milestone_notification)
        assert "milestone_notifications" in source
        assert "auto_notify" in source

    def test_milestone_logs_event(self):
        """Verify milestone achievement is logged to activity feed."""
        import inspect

        from app.services.milestone_service import fire_milestone_notification

        source = inspect.getsource(fire_milestone_notification)
        assert "event_logger.log" in source
        assert "milestone_achieved" in source

    def test_milestone_sends_email_notification(self):
        """Verify milestone fires Celery email task."""
        import inspect

        from app.services.milestone_service import fire_milestone_notification

        source = inspect.getsource(fire_milestone_notification)
        assert "send_milestone_notification" in source
        assert ".delay(" in source

    def test_idempotent_milestone_detection(self):
        """Verify milestone checks for existing notification before re-firing."""
        import inspect

        from app.services.milestone_service import check_phase_milestone

        source = inspect.getsource(check_phase_milestone)
        assert "already_fired" in source
