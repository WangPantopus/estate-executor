"""Report generation API routes.

Supports synchronous generation (returns file directly) and async generation
via Celery for large reports (returns job_id for polling).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.services import report_service

router = APIRouter()

_REPORT_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}


def _check_report_permission(stakeholder: Stakeholder) -> None:
    if stakeholder.role not in _REPORT_ROLES:
        raise PermissionDeniedError(detail="Only admins and professionals can generate reports")


# ---------------------------------------------------------------------------
# GET /reports — List available report types
# ---------------------------------------------------------------------------


@router.get("")
async def list_report_types(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
) -> list[dict]:
    """List available report types with their supported formats."""
    _check_report_permission(stakeholder)

    return [
        {
            "type": report_type,
            "label": config["label"],
            "formats": config["formats"],
        }
        for report_type, config in report_service.REPORT_GENERATORS.items()
    ]


# ---------------------------------------------------------------------------
# POST /reports/{report_type} — Generate a report (sync download)
# ---------------------------------------------------------------------------


@router.post("/{report_type}")
async def generate_report(
    firm_id: UUID,
    matter_id: UUID,
    report_type: str,
    format: str = Query("pdf", description="Output format: pdf or xlsx"),
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate a report and return it as a file download.

    Supported report types:
    - matter-summary (pdf)
    - asset-inventory (pdf, xlsx)
    - task-audit (pdf, xlsx)
    - distribution-ledger (pdf)
    - time-tracking (xlsx)
    """
    _check_report_permission(stakeholder)

    try:
        content, filename, content_type = await report_service.generate_report(
            db,
            matter_id=matter_id,
            report_type=report_type,
            output_format=format,
        )
    except ValueError as exc:
        raise ValidationError(detail=str(exc))

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


# ---------------------------------------------------------------------------
# POST /reports/{report_type}/async — Generate via Celery (for large reports)
# ---------------------------------------------------------------------------


@router.post("/{report_type}/async")
async def generate_report_async(
    firm_id: UUID,
    matter_id: UUID,
    report_type: str,
    format: str = Query("pdf", description="Output format: pdf or xlsx"),
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
) -> dict:
    """Queue async report generation via Celery. Returns a job_id for polling."""
    _check_report_permission(stakeholder)

    if report_type not in report_service.REPORT_GENERATORS:
        raise ValidationError(detail=f"Unknown report type: {report_type}")

    config = report_service.REPORT_GENERATORS[report_type]
    if format not in config["formats"]:
        raise ValidationError(
            detail=f"Format '{format}' not supported for '{report_type}'"
        )

    from app.workers.report_tasks import generate_report_task

    import uuid as uuid_mod

    job_id = str(uuid_mod.uuid4())
    generate_report_task.delay(
        job_id=job_id,
        matter_id=str(matter_id),
        report_type=report_type,
        output_format=format,
    )

    return {"job_id": job_id, "status": "processing"}


# ---------------------------------------------------------------------------
# GET /reports/jobs/{job_id} — Check async job status
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}")
async def get_report_job_status(
    firm_id: UUID,
    matter_id: UUID,
    job_id: str,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
) -> dict:
    """Check the status of an async report generation job."""
    from app.workers.celery_app import celery_app

    result = celery_app.AsyncResult(job_id)

    if result.ready():
        if result.successful():
            data = result.result
            return {
                "job_id": job_id,
                "status": "completed",
                "download_url": data.get("download_url") if isinstance(data, dict) else None,
                "filename": data.get("filename") if isinstance(data, dict) else None,
            }
        return {"job_id": job_id, "status": "failed"}

    return {"job_id": job_id, "status": "processing"}
