"""Unit tests for email service and template rendering."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestTemplateRendering:
    """Verify all Jinja2 email templates render without errors."""

    def _render(self, template_name: str, **kwargs):
        from app.services.email_service import render_template

        defaults = {
            "recipient_name": "Jane Smith",
            "decedent_name": "John Smith",
            "firm_name": "Smith & Associates LLP",
            "frontend_url": "http://localhost:3000",
        }
        defaults.update(kwargs)
        return render_template(template_name, **defaults)

    def test_stakeholder_invitation_renders(self):
        html = self._render(
            "stakeholder_invitation.html",
            inviter_name="Tom Wilson",
            role_label="Beneficiary",
            invite_url="http://localhost:3000/invite/abc123",
        )
        assert "You've Been Invited" in html
        assert "Tom Wilson" in html
        assert "John Smith" in html
        assert "Beneficiary" in html
        assert "http://localhost:3000/invite/abc123" in html
        assert "Accept Invitation" in html

    def test_task_assigned_renders(self):
        html = self._render(
            "task_assigned.html",
            task_title="Obtain Death Certificates",
            task_description="Order 10 certified copies of the death certificate.",
            due_date="2026-04-15",
            phase="Immediate",
            priority="Critical",
            task_url="http://localhost:3000/matters/123/tasks?task=456",
        )
        assert "New Task Assigned" in html
        assert "Obtain Death Certificates" in html
        assert "2026-04-15" in html
        assert "Critical" in html
        assert "View Task" in html

    def test_task_overdue_renders(self):
        html = self._render(
            "task_overdue.html",
            task_title="File Probate Petition",
            due_date="2026-03-01",
            status="In Progress",
            assigned_to_name="Bob Jones",
            task_url="http://localhost:3000/matters/123/tasks?task=456",
        )
        assert "Task Overdue" in html
        assert "File Probate Petition" in html
        assert "2026-03-01" in html
        assert "Bob Jones" in html

    def test_deadline_reminder_renders(self):
        html = self._render(
            "deadline_reminder.html",
            deadline_title="Federal Estate Tax Return (Form 706)",
            deadline_description="Due 9 months from date of death.",
            due_date="2026-09-15",
            days_remaining=30,
            linked_task="Prepare Form 706",
            calendar_url="http://localhost:3000/matters/123/deadlines",
        )
        assert "Deadline Approaching" in html
        assert "Federal Estate Tax Return" in html
        assert "30" in html
        assert "View Calendar" in html

    def test_deadline_missed_renders(self):
        html = self._render(
            "deadline_missed.html",
            deadline_title="Creditor Claims Window",
            deadline_description="All creditor claims must be filed by this date.",
            due_date="2026-02-28",
            days_overdue=5,
            linked_task=None,
            calendar_url="http://localhost:3000/matters/123/deadlines",
        )
        assert "DEADLINE MISSED" in html
        assert "Creditor Claims Window" in html
        assert "5" in html
        assert "IMMEDIATE ATTENTION REQUIRED" in html

    def test_milestone_notification_renders(self):
        html = self._render(
            "milestone_notification.html",
            milestone="All assets inventoried and valued",
            milestone_description="The asset inventory phase is now complete.",
            progress_summary="Phase 2 of 4 complete",
            matter_url="http://localhost:3000/matters/123",
        )
        assert "Milestone Reached" in html
        assert "MILESTONE ACHIEVED" in html
        assert "All assets inventoried" in html
        assert "View Progress" in html

    def test_distribution_notice_renders(self):
        html = self._render(
            "distribution_notice.html",
            distribution_details="Final distribution of liquid assets per the Last Will.",
            amount="$150,000.00",
            acknowledge_url="http://localhost:3000/matters/123/communications?acknowledge=456",
        )
        assert "Distribution Notice" in html
        assert "$150,000.00" in html
        assert "View &amp; Acknowledge" in html

    def test_document_request_renders(self):
        html = self._render(
            "document_request.html",
            requester_name="Attorney Sarah Lee",
            doc_type="Death Certificate",
            reason="Required for probate filing.",
            upload_url="http://localhost:3000/matters/123/documents?upload=true",
        )
        assert "Document Requested" in html
        assert "Attorney Sarah Lee" in html
        assert "Death Certificate" in html
        assert "Upload Document" in html

    def test_templates_are_mobile_responsive(self):
        """All templates should include responsive meta tags and media queries."""
        html = self._render(
            "stakeholder_invitation.html",
            inviter_name="Test",
            role_label="Beneficiary",
            invite_url="http://localhost:3000/invite/test",
        )
        assert "viewport" in html
        assert "@media" in html
        assert "max-width: 620px" in html

    def test_template_includes_footer(self):
        html = self._render(
            "task_assigned.html",
            task_title="Test",
            task_url="http://localhost:3000",
        )
        assert "All rights reserved" in html

    def test_template_white_label_firm_name(self):
        """When firm_name is provided, header should show it."""
        html = self._render(
            "task_assigned.html",
            task_title="Test",
            task_url="http://localhost:3000",
            firm_name="Prestigious Law Firm",
        )
        assert "Prestigious Law Firm" in html
        assert "Powered by Estate Executor" in html

    def test_template_no_firm_name_shows_default(self):
        """When no firm_name, header should show 'Estate Executor'."""
        html = self._render(
            "task_assigned.html",
            task_title="Test",
            task_url="http://localhost:3000",
            firm_name=None,
        )
        assert "Estate Executor" in html


class TestEmailService:
    """Test the email service send functions."""

    @patch("app.services.email_service.settings")
    def test_send_via_mailpit_in_dev(self, mock_settings):
        mock_settings.is_development = True
        mock_settings.email_from = "test@test.com"
        mock_settings.mailpit_smtp_host = "localhost"
        mock_settings.mailpit_smtp_port = 1025

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            from app.services.email_service import send_email

            result = send_email(
                to="user@example.com",
                subject="Test",
                html="<p>Hello</p>",
            )

            assert result["status"] == "sent"
            assert result["provider"] == "mailpit"
            mock_smtp.assert_called_once_with("localhost", 1025)

    @patch("app.services.email_service.settings")
    def test_send_via_resend_in_prod(self, mock_settings):
        mock_settings.is_development = False
        mock_settings.resend_api_key = "re_test_key"
        mock_settings.email_from = "test@test.com"

        with patch("resend.Emails") as mock_emails:
            mock_emails.send.return_value = {"id": "resend_123"}

            from app.services.email_service import send_email

            result = send_email(
                to="user@example.com",
                subject="Test",
                html="<p>Hello</p>",
            )

            assert result["status"] == "sent"
            assert result["provider"] == "resend"
            assert result["resend_id"] == "resend_123"


class TestEmailLogModel:
    """Test the EmailLog model structure."""

    def test_email_log_has_required_fields(self):
        from app.models.email_logs import EmailLog

        mapper = EmailLog.__table__
        column_names = {c.name for c in mapper.columns}

        assert "id" in column_names
        assert "to_address" in column_names
        assert "subject" in column_names
        assert "template" in column_names
        assert "status" in column_names
        assert "resend_id" in column_names
        assert "error" in column_names
        assert "sent_at" in column_names
        assert "created_at" in column_names

    def test_email_log_does_not_store_body(self):
        """Email body should NOT be stored (PII concern)."""
        from app.models.email_logs import EmailLog

        column_names = {c.name for c in EmailLog.__table__.columns}
        assert "body" not in column_names
        assert "html_body" not in column_names


class TestNotificationTasks:
    """Test that notification task functions are registered."""

    @pytest.fixture(autouse=True)
    def _import_tasks(self):
        """Ensure task modules are imported so tasks are registered with Celery."""
        import app.workers.notification_tasks  # noqa: F401

    def test_send_email_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_email" in celery_app.tasks

    def test_send_templated_email_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_templated_email" in celery_app.tasks

    def test_send_stakeholder_invitation_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_stakeholder_invitation" in celery_app.tasks

    def test_send_task_assignment_task_registered(self):
        from app.workers.celery_app import celery_app

        assert (
            "app.workers.notification_tasks.send_task_assignment_notification" in celery_app.tasks
        )

    def test_send_deadline_reminder_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_deadline_reminder" in celery_app.tasks

    def test_send_deadline_missed_task_registered(self):
        from app.workers.celery_app import celery_app

        assert (
            "app.workers.notification_tasks.send_deadline_missed_notification" in celery_app.tasks
        )

    def test_send_milestone_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_milestone_notification" in celery_app.tasks

    def test_send_distribution_notice_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_distribution_notice" in celery_app.tasks

    def test_send_document_request_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_document_request" in celery_app.tasks

    def test_send_task_overdue_task_registered(self):
        from app.workers.celery_app import celery_app

        assert "app.workers.notification_tasks.send_task_overdue_notification" in celery_app.tasks
