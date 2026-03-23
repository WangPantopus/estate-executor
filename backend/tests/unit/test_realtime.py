"""Unit tests for real-time WebSocket infrastructure."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEventLoggerRealtimePublishing:
    """Verify EventLogger publishes to Redis pub/sub after logging."""

    @pytest.mark.asyncio
    async def test_log_publishes_event_new(self):
        """Every logged event should publish an 'event_new' to Redis."""
        import uuid

        from app.core.events import EventLogger
        from app.models.enums import ActorType

        logger = EventLogger()

        # Mock the db session
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        matter_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            await logger.log(
                mock_db,
                matter_id=matter_id,
                actor_id=actor_id,
                actor_type=ActorType.user,
                entity_type="task",
                entity_id=entity_id,
                action="updated",
                changes={"status": {"from": "not_started", "to": "in_progress"}},
            )

            # Should have been called at least once for event_new
            calls = mock_publish.call_args_list
            event_names = [c.kwargs["event"] for c in calls]
            assert "event_new" in event_names

    @pytest.mark.asyncio
    async def test_log_publishes_typed_event_for_mapped_actions(self):
        """Task updates should also publish 'task_updated'."""
        import uuid

        from app.core.events import EventLogger
        from app.models.enums import ActorType

        logger = EventLogger()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            await logger.log(
                mock_db,
                matter_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                actor_type=ActorType.user,
                entity_type="task",
                entity_id=uuid.uuid4(),
                action="completed",
            )

            calls = mock_publish.call_args_list
            event_names = [c.kwargs["event"] for c in calls]
            assert "task_updated" in event_names
            assert "event_new" in event_names

    @pytest.mark.asyncio
    async def test_log_publishes_document_uploaded(self):
        """Document creation should publish 'document_uploaded'."""
        import uuid

        from app.core.events import EventLogger
        from app.models.enums import ActorType

        logger = EventLogger()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            await logger.log(
                mock_db,
                matter_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                actor_type=ActorType.user,
                entity_type="document",
                entity_id=uuid.uuid4(),
                action="uploaded",
            )

            calls = mock_publish.call_args_list
            event_names = [c.kwargs["event"] for c in calls]
            assert "document_uploaded" in event_names

    @pytest.mark.asyncio
    async def test_log_publishes_communication_new(self):
        """Communication creation should publish 'communication_new'."""
        import uuid

        from app.core.events import EventLogger
        from app.models.enums import ActorType

        logger = EventLogger()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            await logger.log(
                mock_db,
                matter_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                actor_type=ActorType.user,
                entity_type="communication",
                entity_id=uuid.uuid4(),
                action="created",
            )

            calls = mock_publish.call_args_list
            event_names = [c.kwargs["event"] for c in calls]
            assert "communication_new" in event_names

    @pytest.mark.asyncio
    async def test_log_does_not_emit_typed_event_for_unknown_action(self):
        """Unknown entity_type/action combos should only emit event_new."""
        import uuid

        from app.core.events import EventLogger
        from app.models.enums import ActorType

        logger = EventLogger()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            await logger.log(
                mock_db,
                matter_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                actor_type=ActorType.system,
                entity_type="matter",
                entity_id=uuid.uuid4(),
                action="phase_changed",
            )

            calls = mock_publish.call_args_list
            # Only event_new, no typed event
            assert len(calls) == 1
            assert calls[0].kwargs["event"] == "event_new"

    @pytest.mark.asyncio
    async def test_publish_failure_does_not_raise(self):
        """Redis publish failures should not break the event logging flow."""
        import uuid

        from app.core.events import EventLogger
        from app.models.enums import ActorType

        logger = EventLogger()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch(
            "app.realtime.publisher.publish_realtime_event",
            side_effect=Exception("Redis down"),
        ):
            # Should not raise
            event = await logger.log(
                mock_db,
                matter_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                actor_type=ActorType.user,
                entity_type="task",
                entity_id=uuid.uuid4(),
                action="updated",
            )
            assert event is not None


class TestRealtimePublisher:
    """Test the Redis pub/sub publisher."""

    def test_publish_realtime_event_calls_redis_publish(self):
        with patch("app.realtime.publisher._get_redis") as mock_get_redis:
            mock_redis = MagicMock()
            mock_get_redis.return_value = mock_redis

            from app.realtime.publisher import publish_realtime_event

            publish_realtime_event(
                matter_id="test-matter-id",
                event="task_updated",
                data={"task_id": "123", "changes": {"status": "completed"}},
            )

            mock_redis.publish.assert_called_once()
            channel, payload = mock_redis.publish.call_args[0]
            assert channel == "estate_executor:realtime"

            parsed = json.loads(payload)
            assert parsed["matter_id"] == "test-matter-id"
            assert parsed["event"] == "task_updated"
            assert parsed["data"]["task_id"] == "123"

    def test_publish_failure_does_not_raise(self):
        with patch("app.realtime.publisher._get_redis") as mock_get_redis:
            mock_redis = MagicMock()
            mock_redis.publish.side_effect = Exception("Redis down")
            mock_get_redis.return_value = mock_redis

            from app.realtime.publisher import publish_realtime_event

            # Should not raise
            publish_realtime_event(
                matter_id="test-matter-id",
                event="task_updated",
                data={},
            )

    def test_emit_task_updated_helper(self):
        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            from app.realtime.publisher import emit_task_updated

            emit_task_updated(
                "matter-1",
                "task-1",
                {"status": "completed"},
                "actor-1",
            )

            mock_publish.assert_called_once_with(
                matter_id="matter-1",
                event="task_updated",
                data={
                    "task_id": "task-1",
                    "changes": {"status": "completed"},
                    "actor": "actor-1",
                },
            )

    def test_emit_document_uploaded_helper(self):
        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            from app.realtime.publisher import emit_document_uploaded

            emit_document_uploaded("matter-1", "doc-1", "will.pdf", "uploader-1")

            mock_publish.assert_called_once_with(
                matter_id="matter-1",
                event="document_uploaded",
                data={
                    "document_id": "doc-1",
                    "filename": "will.pdf",
                    "uploaded_by": "uploader-1",
                },
            )

    def test_emit_deadline_updated_helper(self):
        with patch("app.realtime.publisher.publish_realtime_event") as mock_publish:
            from app.realtime.publisher import emit_deadline_updated

            emit_deadline_updated("matter-1", "dl-1", {"status": "missed"})

            mock_publish.assert_called_once_with(
                matter_id="matter-1",
                event="deadline_updated",
                data={"deadline_id": "dl-1", "changes": {"status": "missed"}},
            )


class TestEventMap:
    """Verify the event mapping covers all expected entity/action pairs."""

    def test_all_task_actions_mapped(self):
        from app.core.events import _EVENT_MAP

        task_actions = ["created", "updated", "completed", "waived", "assigned"]
        for action in task_actions:
            assert ("task", action) in _EVENT_MAP
            assert _EVENT_MAP[("task", action)] == "task_updated"

    def test_document_actions_mapped(self):
        from app.core.events import _EVENT_MAP

        assert _EVENT_MAP[("document", "created")] == "document_uploaded"
        assert _EVENT_MAP[("document", "uploaded")] == "document_uploaded"

    def test_deadline_actions_mapped(self):
        from app.core.events import _EVENT_MAP

        assert _EVENT_MAP[("deadline", "created")] == "deadline_updated"
        assert _EVENT_MAP[("deadline", "updated")] == "deadline_updated"

    def test_communication_action_mapped(self):
        from app.core.events import _EVENT_MAP

        assert _EVENT_MAP[("communication", "created")] == "communication_new"

    def test_stakeholder_actions_mapped(self):
        from app.core.events import _EVENT_MAP

        assert _EVENT_MAP[("stakeholder", "created")] == "stakeholder_changed"
        assert _EVENT_MAP[("stakeholder", "updated")] == "stakeholder_changed"
        assert _EVENT_MAP[("stakeholder", "removed")] == "stakeholder_changed"


class TestSocketIOServerSetup:
    """Test Socket.IO server configuration."""

    def test_sio_instance_exists(self):
        from app.realtime.server import sio

        assert sio is not None
        assert sio.async_mode == "asgi"

    def test_create_socketio_app_returns_asgi_app(self):
        from app.realtime.server import create_socketio_app

        asgi_app = create_socketio_app()
        assert asgi_app is not None

    def test_matters_namespace_registered(self):
        from app.realtime.server import sio

        # The namespace handler should be registered
        assert "/matters" in sio.namespace_handlers

    def test_broadcast_to_matter_exists(self):
        from app.realtime.server import broadcast_to_matter

        assert callable(broadcast_to_matter)
