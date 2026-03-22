"""Legacy task module — re-exports from specialized task modules.

All tasks have been moved to dedicated modules:
- deadline_tasks: check_deadlines, check_overdue_tasks
- ai_tasks: classify_document, extract_document_data, draft_letter
- document_tasks: generate_bulk_download
- notification_tasks: send_email, send_stakeholder_invitation, etc.

This module provides backward-compatible imports.
"""

from app.workers.ai_tasks import classify_document  # noqa: F401
from app.workers.deadline_tasks import check_deadlines  # noqa: F401
from app.workers.document_tasks import generate_bulk_download as generate_bulk_zip  # noqa: F401
