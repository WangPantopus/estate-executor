"""Email service — send transactional emails via Resend (prod) or Mailpit SMTP (dev).

All outbound emails are logged to the email_logs table (body excluded for PII).
Jinja2 templates live in app/templates/emails/.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import insert

from app.core.config import settings
from app.models.email_logs import EmailLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Jinja2 template environment
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_template(template_name: str, **context: Any) -> str:
    """Render an HTML email template with the given context."""
    template = _jinja_env.get_template(template_name)
    # Inject defaults that templates can use, but allow caller overrides
    defaults = {
        "frontend_url": settings.frontend_url,
        "current_year": datetime.now(UTC).year,
    }
    defaults.update(context)
    return template.render(**defaults)


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------


def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text_fallback: str | None = None,
    template_name: str | None = None,
) -> dict[str, Any]:
    """Send an email via Resend (production) or Mailpit SMTP (development).

    Returns dict with status and provider response info.
    Raises on failure so Celery can retry.
    """
    if settings.is_development:
        return _send_via_mailpit(to=to, subject=subject, html=html, text_fallback=text_fallback)
    return _send_via_resend(to=to, subject=subject, html=html, text_fallback=text_fallback)


def _send_via_resend(
    *, to: str, subject: str, html: str, text_fallback: str | None
) -> dict[str, Any]:
    """Send email using the Resend API."""
    import resend

    resend.api_key = settings.resend_api_key

    params: dict[str, Any] = {
        "from_": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text_fallback:
        params["text"] = text_fallback

    response = resend.Emails.send(params)  # type: ignore[arg-type]
    resend_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)

    logger.info("email_sent_resend", extra={"to": to, "subject": subject, "resend_id": resend_id})
    return {"status": "sent", "provider": "resend", "resend_id": resend_id}


def _send_via_mailpit(
    *, to: str, subject: str, html: str, text_fallback: str | None
) -> dict[str, Any]:
    """Send email via Mailpit SMTP for local development."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to

    if text_fallback:
        msg.attach(MIMEText(text_fallback, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.mailpit_smtp_host, settings.mailpit_smtp_port) as server:
        server.send_message(msg)

    logger.info("email_sent_mailpit", extra={"to": to, "subject": subject})
    return {"status": "sent", "provider": "mailpit"}


# ---------------------------------------------------------------------------
# Logging helper (call from Celery tasks with a sync session)
# ---------------------------------------------------------------------------


def log_email_sync(
    *,
    to: str,
    subject: str,
    template_name: str | None = None,
    status: str = "sent",
    resend_id: str | None = None,
    error: str | None = None,
) -> None:
    """Log an email send using a synchronous DB connection."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    sync_engine = create_engine(settings.database_url_sync)
    with Session(sync_engine) as session:
        session.execute(
            insert(EmailLog).values(
                to_address=to,
                subject=subject,
                template=template_name,
                status=status,
                resend_id=resend_id,
                error=error,
                sent_at=datetime.now(UTC) if status == "sent" else None,
            )
        )
        session.commit()
    sync_engine.dispose()


# ---------------------------------------------------------------------------
# High-level template-based send helpers
# ---------------------------------------------------------------------------


def send_templated_email(
    *,
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Render a Jinja2 template and send the email. Logs the result.

    This is the primary entry point used by Celery notification tasks.
    """
    html = render_template(template_name, **context)

    # Build a plain-text fallback from the subject
    text_fallback = f"{subject}\n\nPlease view this email in an HTML-capable email client."

    try:
        result = send_email(
            to=to,
            subject=subject,
            html=html,
            text_fallback=text_fallback,
            template_name=template_name,
        )
        log_email_sync(
            to=to,
            subject=subject,
            template_name=template_name,
            status="sent",
            resend_id=result.get("resend_id"),
        )
        return result
    except Exception:
        log_email_sync(
            to=to,
            subject=subject,
            template_name=template_name,
            status="failed",
            error="Send failed — will retry",
        )
        raise
