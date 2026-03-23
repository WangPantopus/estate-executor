"""Unit tests for Celery setup and worker infrastructure."""

from __future__ import annotations


class TestCeleryAppConfiguration:
    """Verify celery_app.py configuration."""

    def test_broker_uses_redis(self):
        from app.workers.celery_app import celery_app

        assert "redis://" in celery_app.conf.broker_url

    def test_result_backend_uses_redis(self):
        from app.workers.celery_app import celery_app

        assert "redis://" in celery_app.conf.result_backend

    def test_serializer_is_json(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"

    def test_accept_content_is_json(self):
        from app.workers.celery_app import celery_app

        assert "json" in celery_app.conf.accept_content

    def test_timezone_is_utc(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.timezone == "UTC"

    def test_enable_utc(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.enable_utc is True


class TestTaskRouting:
    """Verify task routing to correct queues."""

    def test_ai_tasks_route_to_ai_queue(self):
        from app.workers.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes["app.workers.ai_tasks.*"]["queue"] == "ai"

    def test_notification_tasks_route_to_notifications_queue(self):
        from app.workers.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes["app.workers.notification_tasks.*"]["queue"] == "notifications"

    def test_document_tasks_route_to_documents_queue(self):
        from app.workers.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes["app.workers.document_tasks.*"]["queue"] == "documents"

    def test_default_queue_is_default(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_default_queue == "default"


class TestBeatSchedule:
    """Verify Celery beat schedule configuration."""

    def test_check_deadlines_in_schedule(self):
        from app.workers.celery_app import celery_app

        assert "check-deadlines-hourly" in celery_app.conf.beat_schedule

    def test_check_deadlines_runs_hourly(self):
        from app.workers.celery_app import celery_app

        config = celery_app.conf.beat_schedule["check-deadlines-hourly"]
        assert config["schedule"] == 3600.0

    def test_check_deadlines_task_name(self):
        from app.workers.celery_app import celery_app

        config = celery_app.conf.beat_schedule["check-deadlines-hourly"]
        assert config["task"] == "app.workers.deadline_tasks.check_deadlines"

    def test_check_overdue_tasks_in_schedule(self):
        from app.workers.celery_app import celery_app

        assert "check-overdue-tasks-6h" in celery_app.conf.beat_schedule

    def test_check_overdue_tasks_runs_every_6_hours(self):
        from app.workers.celery_app import celery_app

        config = celery_app.conf.beat_schedule["check-overdue-tasks-6h"]
        assert config["schedule"] == 21600.0

    def test_check_overdue_tasks_task_name(self):
        from app.workers.celery_app import celery_app

        config = celery_app.conf.beat_schedule["check-overdue-tasks-6h"]
        assert config["task"] == "app.workers.deadline_tasks.check_overdue_tasks"


class TestTimeLimits:
    """Verify default time limits."""

    def test_soft_time_limit_is_300(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_soft_time_limit == 300

    def test_hard_time_limit_is_600(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_time_limit == 600


class TestRetryPolicy:
    """Verify retry policy configuration."""

    def test_late_ack_enabled(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_acks_late is True

    def test_reject_on_worker_lost(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_reject_on_worker_lost is True

    def test_store_errors(self):
        from app.workers.celery_app import celery_app

        assert celery_app.conf.task_store_errors_even_if_ignored is True


class TestNotificationTasks:
    """Verify notification task definitions."""

    def test_send_email_exists(self):
        from app.workers.notification_tasks import send_email

        assert callable(send_email)
        assert send_email.name == "app.workers.notification_tasks.send_email"

    def test_send_stakeholder_invitation_exists(self):
        from app.workers.notification_tasks import send_stakeholder_invitation

        assert callable(send_stakeholder_invitation)
        expected = "app.workers.notification_tasks.send_stakeholder_invitation"
        assert send_stakeholder_invitation.name == expected

    def test_send_task_assignment_notification_exists(self):
        from app.workers.notification_tasks import send_task_assignment_notification

        assert callable(send_task_assignment_notification)
        expected = "app.workers.notification_tasks.send_task_assignment_notification"
        assert send_task_assignment_notification.name == expected

    def test_send_deadline_reminder_exists(self):
        from app.workers.notification_tasks import send_deadline_reminder

        assert callable(send_deadline_reminder)
        expected = "app.workers.notification_tasks.send_deadline_reminder"
        assert send_deadline_reminder.name == expected

    def test_send_milestone_notification_exists(self):
        from app.workers.notification_tasks import send_milestone_notification

        assert callable(send_milestone_notification)
        expected = "app.workers.notification_tasks.send_milestone_notification"
        assert send_milestone_notification.name == expected


class TestAITasks:
    """Verify AI task definitions."""

    def test_classify_document_exists(self):
        from app.workers.ai_tasks import classify_document

        assert callable(classify_document)
        assert classify_document.name == "app.workers.ai_tasks.classify_document"

    def test_extract_document_data_exists(self):
        from app.workers.ai_tasks import extract_document_data

        assert callable(extract_document_data)
        assert extract_document_data.name == "app.workers.ai_tasks.extract_document_data"

    def test_draft_letter_exists(self):
        from app.workers.ai_tasks import draft_letter

        assert callable(draft_letter)
        assert draft_letter.name == "app.workers.ai_tasks.draft_letter"

    def test_classify_document_has_custom_time_limits(self):
        """AI tasks should have custom (shorter) time limits."""
        from app.workers.ai_tasks import classify_document

        assert classify_document.soft_time_limit == 120
        assert classify_document.time_limit == 180

    def test_draft_letter_has_longer_time_limits(self):
        """Letter drafting may take longer than classification."""
        from app.workers.ai_tasks import draft_letter

        assert draft_letter.soft_time_limit == 180
        assert draft_letter.time_limit == 300


class TestDocumentTasks:
    """Verify document task definitions."""

    def test_generate_bulk_download_exists(self):
        from app.workers.document_tasks import generate_bulk_download

        assert callable(generate_bulk_download)
        assert generate_bulk_download.name == "app.workers.document_tasks.generate_bulk_download"

    def test_bulk_download_has_long_time_limits(self):
        """Bulk download may process many files — needs longer limits."""
        from app.workers.document_tasks import generate_bulk_download

        assert generate_bulk_download.soft_time_limit == 600
        assert generate_bulk_download.time_limit == 900


class TestDeadlineTasks:
    """Verify deadline task definitions."""

    def test_check_deadlines_exists(self):
        from app.workers.deadline_tasks import check_deadlines

        assert callable(check_deadlines)
        assert check_deadlines.name == "app.workers.deadline_tasks.check_deadlines"

    def test_check_overdue_tasks_exists(self):
        from app.workers.deadline_tasks import check_overdue_tasks

        assert callable(check_overdue_tasks)
        assert check_overdue_tasks.name == "app.workers.deadline_tasks.check_overdue_tasks"


class TestBackwardCompatibility:
    """Verify old import paths still work via tasks.py re-exports."""

    def test_classify_document_from_old_path(self):
        from app.workers.tasks import classify_document

        assert callable(classify_document)

    def test_check_deadlines_from_old_path(self):
        from app.workers.tasks import check_deadlines

        assert callable(check_deadlines)

    def test_generate_bulk_zip_from_old_path(self):
        from app.workers.tasks import generate_bulk_zip

        assert callable(generate_bulk_zip)


class TestTaskQueueAssignment:
    """Verify tasks would be routed to their correct queues based on naming."""

    def _get_queue_for_task(self, task_name: str) -> str:
        import fnmatch

        from app.workers.celery_app import celery_app

        routes = celery_app.conf.task_routes
        for pattern, config in routes.items():
            if fnmatch.fnmatch(task_name, pattern):
                return config["queue"]
        return celery_app.conf.task_default_queue

    def test_ai_classify_routes_to_ai(self):
        assert self._get_queue_for_task("app.workers.ai_tasks.classify_document") == "ai"

    def test_ai_extract_routes_to_ai(self):
        assert self._get_queue_for_task("app.workers.ai_tasks.extract_document_data") == "ai"

    def test_notification_email_routes_to_notifications(self):
        task = "app.workers.notification_tasks.send_email"
        assert self._get_queue_for_task(task) == "notifications"

    def test_document_bulk_routes_to_documents(self):
        task = "app.workers.document_tasks.generate_bulk_download"
        assert self._get_queue_for_task(task) == "documents"

    def test_deadline_routes_to_default(self):
        assert self._get_queue_for_task("app.workers.deadline_tasks.check_deadlines") == "default"
