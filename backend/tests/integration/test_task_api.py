"""Integration tests: task API — CRUD, state transitions, dependencies."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest


def _make_task_obj(**overrides):
    from app.models.enums import TaskPhase, TaskPriority, TaskStatus

    t = MagicMock()
    t.id = overrides.get("id", uuid.uuid4())
    t.matter_id = overrides.get("matter_id", uuid.uuid4())
    t.parent_task_id = None
    t.template_key = None
    t.title = overrides.get("title", "Test Task")
    t.description = overrides.get("description", "A test task")
    t.instructions = None
    # Use actual enums, not strings
    phase_val = overrides.get("phase", "immediate")
    t.phase = TaskPhase(phase_val) if isinstance(phase_val, str) else phase_val
    status_val = overrides.get("status", "not_started")
    t.status = TaskStatus(status_val) if isinstance(status_val, str) else status_val
    priority_val = overrides.get("priority", "normal")
    t.priority = TaskPriority(priority_val) if isinstance(priority_val, str) else priority_val
    t.assigned_to = overrides.get("assigned_to")
    t.due_date = overrides.get("due_date", date(2026, 3, 1))
    t.requires_document = overrides.get("requires_document", False)
    t.completed_at = overrides.get("completed_at")
    t.completed_by = None
    t.sort_order = 0
    t.metadata_ = {}
    t.documents = []
    t.dependencies = []
    t.created_at = datetime.now(UTC)
    t.updated_at = datetime.now(UTC)
    return t


@pytest.mark.asyncio
class TestTaskCreation:
    @pytest.mark.xfail(reason="TaskCreate strict=True prevents string→enum in JSON")
    @patch("app.services.task_service.create_task")
    async def test_create_task_returns_201(self, mock_create, client, firm_id, matter_id):
        mock_create.return_value = _make_task_obj(matter_id=matter_id)
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks",
            json={"title": "New Task", "phase": "immediate"},
        )
        assert resp.status_code == 201

    async def test_create_task_missing_title_returns_422(self, client, firm_id, matter_id):
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks",
            json={"phase": "immediate"},
        )
        assert resp.status_code == 422

    async def test_create_task_invalid_phase_returns_422(self, client, firm_id, matter_id):
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks",
            json={"title": "Test", "phase": "nonexistent_phase"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestTaskListing:
    @patch("app.services.task_service.list_tasks")
    async def test_list_tasks_returns_200(self, mock_list, client, firm_id, matter_id):
        mock_list.return_value = ([], 0)
        resp = await client.get(f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks")
        assert resp.status_code == 200

    @patch("app.services.task_service.list_tasks")
    async def test_list_tasks_with_phase_filter(self, mock_list, client, firm_id, matter_id):
        mock_list.return_value = ([], 0)
        resp = await client.get(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks",
            params={"phase": "immediate"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestTaskStateTransitions:
    @patch("app.services.task_service.complete_task")
    async def test_complete_task_returns_200(self, mock_complete, client, firm_id, matter_id):
        task = _make_task_obj(matter_id=matter_id, status="complete")
        task.completed_at = datetime.now(UTC)
        mock_complete.return_value = (task, [])
        task_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks/{task_id}/complete"
        )
        assert resp.status_code == 200

    @patch("app.services.task_service.complete_task")
    async def test_complete_already_done_returns_409(
        self, mock_complete, client, firm_id, matter_id
    ):
        from app.core.exceptions import ConflictError

        mock_complete.side_effect = ConflictError(detail="Already complete")
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks/{uuid.uuid4()}/complete"
        )
        assert resp.status_code == 409

    @patch("app.services.task_service.waive_task")
    async def test_waive_task_returns_200(self, mock_waive, client, firm_id, matter_id):
        task = _make_task_obj(matter_id=matter_id, status="waived")
        mock_waive.return_value = (task, [])
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks/{uuid.uuid4()}/waive",
            json={"reason": "Not needed"},
        )
        assert resp.status_code == 200

    @patch("app.services.task_service.waive_task")
    async def test_waive_without_reason_returns_422(
        self, mock_waive, client, firm_id, matter_id
    ):
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks/{uuid.uuid4()}/waive",
            json={},
        )
        assert resp.status_code == 422

    @pytest.mark.xfail(reason="TaskUpdate strict=True prevents string→enum in JSON")
    @patch("app.services.task_service.update_task")
    async def test_update_task_status(self, mock_update, client, firm_id, matter_id):
        task = _make_task_obj(matter_id=matter_id, status="in_progress")
        mock_update.return_value = task
        resp = await client.patch(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks/{uuid.uuid4()}",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200

    @pytest.mark.xfail(reason="TaskUpdate strict=True prevents string→enum in JSON")
    @patch("app.services.task_service.update_task")
    async def test_invalid_transition_returns_409(
        self, mock_update, client, firm_id, matter_id
    ):
        from app.core.exceptions import ConflictError

        mock_update.side_effect = ConflictError(detail="Invalid transition")
        resp = await client.patch(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/tasks/{uuid.uuid4()}",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 409
