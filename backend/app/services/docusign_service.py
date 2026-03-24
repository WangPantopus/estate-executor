"""DocuSign envelope service — send, track, receive signed documents."""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import func, select

from app.core.events import event_logger
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.documents import Document
from app.models.enums import (
    ActorType,
    IntegrationProvider,
    IntegrationStatus,
    SignatureRequestStatus,
    SignatureRequestType,
)
from app.models.integration_connections import IntegrationConnection
from app.models.signature_requests import SignatureRequest
from app.services.docusign_client import (
    DocuSignAPI,
    build_authorize_url,
    exchange_code_for_tokens,
    generate_state,
    get_user_info,
    refresh_access_token,
    token_expires_at,
)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ─── Connection management (reuses IntegrationConnection) ───────────────────


async def get_connection(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
) -> IntegrationConnection | None:
    result = await db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.firm_id == firm_id,
            IntegrationConnection.provider == IntegrationProvider.docusign,
        )
    )
    return result.scalar_one_or_none()


async def get_connection_or_404(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
) -> IntegrationConnection:
    conn = await get_connection(db, firm_id=firm_id)
    if conn is None:
        raise NotFoundError(detail="DocuSign integration not connected")
    return conn


async def initiate_oauth(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, str]:
    state = generate_state()

    conn = await get_connection(db, firm_id=firm_id)
    if conn and conn.status == IntegrationStatus.connected:
        raise ConflictError(detail="DocuSign is already connected. Disconnect first.")

    if conn is None:
        conn = IntegrationConnection(
            firm_id=firm_id,
            provider=IntegrationProvider.docusign,
            status=IntegrationStatus.pending,
            connected_by=current_user.user_id,
        )
        db.add(conn)

    conn.status = IntegrationStatus.pending
    conn.settings = {**conn.settings, "oauth_state": state}
    conn.connected_by = current_user.user_id
    await db.flush()

    return {"authorize_url": build_authorize_url(state), "state": state}


async def complete_oauth(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    code: str,
    state: str,
) -> IntegrationConnection:
    conn = await get_connection(db, firm_id=firm_id)
    if conn is None:
        raise NotFoundError(detail="No pending DocuSign connection found")

    stored_state = conn.settings.get("oauth_state")
    if not stored_state or stored_state != state:
        raise ValidationError(detail="Invalid OAuth state parameter")

    # Invalidate state immediately
    new_settings = {k: v for k, v in conn.settings.items() if k != "oauth_state"}
    conn.settings = new_settings
    await db.flush()

    token_data = await exchange_code_for_tokens(code)
    conn.access_token = token_data.get("access_token")
    conn.refresh_token = token_data.get("refresh_token")
    conn.token_expires_at = token_expires_at(token_data.get("expires_in"))

    # Fetch account info to get the account ID (needed for all API calls)
    try:
        user_info = await get_user_info(conn.access_token)
        accounts = user_info.get("accounts", [])
        if accounts:
            default = next((a for a in accounts if a.get("is_default")), accounts[0])
            conn.external_account_id = default.get("account_id", "")
            conn.external_account_name = default.get("account_name", user_info.get("name", ""))
            # Store base_uri for API calls
            new_settings["api_base_uri"] = default.get("base_uri", "")
        conn.status = IntegrationStatus.connected
    except httpx.HTTPError:
        logger.error("docusign_account_fetch_failed", exc_info=True)
        conn.status = IntegrationStatus.error
        conn.last_sync_error = "Failed to verify DocuSign account"

    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=conn.connected_by,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="connected",
        metadata={
            "provider": "docusign",
            "account": conn.external_account_name,
        },
    )

    return conn


async def disconnect(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    conn = await get_connection_or_404(db, firm_id=firm_id)
    conn.status = IntegrationStatus.disconnected
    conn.access_token = None
    conn.refresh_token = None
    conn.token_expires_at = None
    conn.disconnected_at = datetime.now(UTC)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="disconnected",
        metadata={"provider": "docusign"},
    )


# ─── Token management ────────────────────────────────────────────────────────


async def _ensure_valid_token(db: AsyncSession, conn: IntegrationConnection) -> DocuSignAPI:
    """Ensure token is valid and return a configured API client."""
    if not conn.access_token or not conn.refresh_token:
        raise ValidationError(detail="DocuSign not connected. Please reconnect.")

    if conn.token_expires_at and conn.token_expires_at <= datetime.now(UTC):
        token_data = await refresh_access_token(conn.refresh_token)
        conn.access_token = token_data.get("access_token")
        conn.refresh_token = token_data.get("refresh_token", conn.refresh_token)
        conn.token_expires_at = token_expires_at(token_data.get("expires_in"))
        await db.flush()

    account_id = conn.external_account_id or ""
    return DocuSignAPI(conn.access_token, account_id)


# ─── Send for signature ─────────────────────────────────────────────────────


async def send_for_signature(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    matter_id: uuid.UUID,
    document_id: uuid.UUID,
    request_type: str,
    subject: str,
    message: str | None,
    signers: list[dict[str, Any]],
    stakeholder_id: uuid.UUID,
    current_user: CurrentUser,
) -> SignatureRequest:
    """Create a DocuSign envelope and send document for signature."""
    conn = await get_connection_or_404(db, firm_id=firm_id)
    api = await _ensure_valid_token(db, conn)

    # Get the document
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.matter_id == matter_id)
    )
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError(detail="Document not found")

    # Download document content from S3 for embedding in envelope
    from app.services import storage_service

    try:
        doc_bytes = storage_service.download_file(doc.storage_key)
        doc_b64 = base64.b64encode(doc_bytes).decode()
    except Exception as e:
        logger.error("docusign_doc_download_failed", exc_info=True)
        raise ValidationError(detail="Failed to retrieve document for signing") from e

    # Build DocuSign envelope definition
    ds_signers = []
    for i, signer in enumerate(signers, start=1):
        ds_signer: dict[str, Any] = {
            "email": signer["email"],
            "name": signer["name"],
            "recipientId": str(i),
            "routingOrder": str(i),
        }
        if signer.get("role") == "cc":
            ds_signer["recipientId"] = str(100 + i)
        else:
            # Add a signature tab (sign here) for actual signers
            ds_signer["tabs"] = {
                "signHereTabs": [
                    {
                        "anchorString": "/sig/",
                        "anchorUnits": "pixels",
                        "anchorXOffset": "0",
                        "anchorYOffset": "0",
                    }
                ],
                "dateSignedTabs": [
                    {
                        "anchorString": "/date/",
                        "anchorUnits": "pixels",
                        "anchorXOffset": "0",
                        "anchorYOffset": "0",
                    }
                ],
            }
        ds_signers.append(ds_signer)

    # Separate signers and CC recipients
    actual_signers = [s for s in ds_signers if int(s["recipientId"]) < 100]
    cc_recipients = [s for s in ds_signers if int(s["recipientId"]) >= 100]

    envelope_def = {
        "emailSubject": subject,
        "emailBlurb": message or "",
        "documents": [
            {
                "documentBase64": doc_b64,
                "name": doc.filename,
                "fileExtension": doc.filename.rsplit(".", 1)[-1] if "." in doc.filename else "pdf",
                "documentId": "1",
            }
        ],
        "recipients": {
            "signers": actual_signers,
            "carbonCopies": cc_recipients,
        },
        "status": "sent",  # Send immediately
    }

    try:
        result = await api.create_envelope(envelope_def)
    except httpx.HTTPError as e:
        logger.error("docusign_create_envelope_failed", exc_info=True)
        raise ValidationError(detail=f"Failed to send for signature: {e}") from e

    envelope_id = result.get("envelopeId", "")
    if not envelope_id:
        raise ValidationError(detail="DocuSign did not return an envelope ID")

    # Create signature request record
    sig_type = (
        SignatureRequestType(request_type)
        if request_type in SignatureRequestType.__members__
        else SignatureRequestType.general
    )
    sig_req = SignatureRequest(
        matter_id=matter_id,
        document_id=document_id,
        request_type=sig_type,
        status=SignatureRequestStatus.sent,
        envelope_id=envelope_id,
        envelope_uri=result.get("uri", ""),
        subject=subject,
        message=message,
        sent_by=stakeholder_id,
        signers=signers,
        sent_at=datetime.now(UTC),
    )
    db.add(sig_req)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="signature_request",
        entity_id=sig_req.id,
        action="sent",
        metadata={
            "envelope_id": envelope_id,
            "type": request_type,
            "signers": len(signers),
        },
    )

    return sig_req


# ─── Track signature status ─────────────────────────────────────────────────


async def get_signature_request(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    matter_id: uuid.UUID,
) -> SignatureRequest:
    result = await db.execute(
        select(SignatureRequest).where(
            SignatureRequest.id == request_id,
            SignatureRequest.matter_id == matter_id,
        )
    )
    sig = result.scalar_one_or_none()
    if sig is None:
        raise NotFoundError(detail="Signature request not found")
    return sig


async def list_signature_requests(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[SignatureRequest], int]:
    count_q = (
        select(func.count())
        .select_from(SignatureRequest)
        .where(SignatureRequest.matter_id == matter_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(SignatureRequest)
        .where(SignatureRequest.matter_id == matter_id)
        .order_by(SignatureRequest.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def refresh_envelope_status(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    request_id: uuid.UUID,
    matter_id: uuid.UUID,
) -> SignatureRequest:
    """Poll DocuSign for the latest envelope status."""
    conn = await get_connection_or_404(db, firm_id=firm_id)
    api = await _ensure_valid_token(db, conn)

    sig_req = await get_signature_request(db, request_id=request_id, matter_id=matter_id)
    if not sig_req.envelope_id:
        return sig_req

    try:
        envelope = await api.get_envelope(sig_req.envelope_id)
        _update_status_from_envelope(sig_req, envelope)

        # Also update signer statuses
        recipients = await api.get_envelope_recipients(sig_req.envelope_id)
        _update_signers_from_recipients(sig_req, recipients)

        await db.flush()
    except httpx.HTTPError:
        logger.warning("docusign_status_refresh_failed", exc_info=True)

    return sig_req


async def void_envelope(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    request_id: uuid.UUID,
    matter_id: uuid.UUID,
    reason: str,
    current_user: CurrentUser,
) -> SignatureRequest:
    """Void a sent envelope."""
    conn = await get_connection_or_404(db, firm_id=firm_id)
    api = await _ensure_valid_token(db, conn)

    sig_req = await get_signature_request(db, request_id=request_id, matter_id=matter_id)
    if sig_req.status in (
        SignatureRequestStatus.completed,
        SignatureRequestStatus.voided,
    ):
        raise ConflictError(detail=f"Cannot void envelope in {sig_req.status.value} status")

    if not sig_req.envelope_id:
        raise ValidationError(detail="No envelope to void")

    try:
        await api.void_envelope(sig_req.envelope_id, reason)
    except httpx.HTTPError as e:
        logger.error("docusign_void_failed", exc_info=True)
        raise ValidationError(detail=f"Failed to void envelope: {e}") from e

    sig_req.status = SignatureRequestStatus.voided
    sig_req.voided_at = datetime.now(UTC)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="signature_request",
        entity_id=sig_req.id,
        action="voided",
        metadata={"reason": reason, "envelope_id": sig_req.envelope_id},
    )

    return sig_req


# ─── Webhook: receive signed documents ──────────────────────────────────────


async def handle_docusign_webhook(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
) -> None:
    """Handle DocuSign Connect webhook notification."""
    event_type = payload.get("event", "")
    envelope_data = payload.get("data", {}).get("envelopeSummary", {})
    envelope_id = envelope_data.get("envelopeId", "")

    if not envelope_id:
        logger.debug("docusign_webhook_no_envelope_id")
        return

    logger.info(
        "docusign_webhook_received",
        extra={"event": event_type, "envelope_id": envelope_id},
    )

    # Find the signature request
    result = await db.execute(
        select(SignatureRequest).where(SignatureRequest.envelope_id == envelope_id)
    )
    sig_req = result.scalar_one_or_none()
    if sig_req is None:
        logger.debug(
            "docusign_webhook_unknown_envelope",
            extra={"envelope_id": envelope_id},
        )
        return

    old_status = sig_req.status

    # Map DocuSign event to our status
    status_map = {
        "envelope-sent": SignatureRequestStatus.sent,
        "envelope-delivered": SignatureRequestStatus.delivered,
        "envelope-completed": SignatureRequestStatus.completed,
        "envelope-declined": SignatureRequestStatus.declined,
        "envelope-voided": SignatureRequestStatus.voided,
    }
    new_status = status_map.get(event_type)
    if new_status:
        sig_req.status = new_status

    # Update signer info from recipients
    recipients = envelope_data.get("recipients", {})
    if recipients:
        _update_signers_from_recipients(sig_req, recipients)

    # Handle completion — download signed document, then mark completed
    if event_type == "envelope-completed":
        download_ok = await _download_and_register_signed_doc(db, sig_req=sig_req)
        sig_req.completed_at = datetime.now(UTC)
        if not download_ok:
            logger.warning(
                "docusign_webhook_download_failed_but_marking_complete",
                extra={"envelope_id": envelope_id},
            )

    if event_type == "envelope-voided":
        sig_req.voided_at = datetime.now(UTC)

    await db.flush()

    if old_status != sig_req.status:
        await event_logger.log(
            db,
            matter_id=sig_req.matter_id,
            actor_id=None,
            actor_type=ActorType.system,
            entity_type="signature_request",
            entity_id=sig_req.id,
            action="status_changed",
            metadata={
                "old_status": old_status.value,
                "new_status": sig_req.status.value,
                "envelope_id": envelope_id,
            },
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _update_status_from_envelope(sig_req: SignatureRequest, envelope: dict[str, Any]) -> None:
    """Update signature request status from DocuSign envelope data."""
    ds_status = envelope.get("status", "")
    mapping = {
        "sent": SignatureRequestStatus.sent,
        "delivered": SignatureRequestStatus.delivered,
        "completed": SignatureRequestStatus.completed,
        "declined": SignatureRequestStatus.declined,
        "voided": SignatureRequestStatus.voided,
    }
    if ds_status in mapping:
        sig_req.status = mapping[ds_status]
    if ds_status == "completed" and not sig_req.completed_at:
        sig_req.completed_at = datetime.now(UTC)


def _update_signers_from_recipients(sig_req: SignatureRequest, recipients: dict[str, Any]) -> None:
    """Update signer statuses from DocuSign recipient data."""
    from sqlalchemy.orm.attributes import flag_modified

    ds_signers = recipients.get("signers", [])
    # Deep-copy to ensure SQLAlchemy detects JSONB mutation
    import copy

    updated_signers = copy.deepcopy(sig_req.signers) if sig_req.signers else []

    for ds_signer in ds_signers:
        email = ds_signer.get("email", "")
        status = ds_signer.get("status", "")
        signed_dt = ds_signer.get("signedDateTime")

        for signer in updated_signers:
            if signer.get("email", "").lower() == email.lower():
                signer["status"] = status
                if signed_dt:
                    signer["signed_at"] = signed_dt
                break

    sig_req.signers = updated_signers
    # Ensure SQLAlchemy detects the JSONB mutation
    if hasattr(sig_req, "_sa_instance_state"):
        flag_modified(sig_req, "signers")


async def _download_and_register_signed_doc(
    db: AsyncSession,
    *,
    sig_req: SignatureRequest,
) -> bool:
    """Download the signed document from DocuSign and register as new version.

    Returns True if download and registration succeeded.
    """
    if not sig_req.envelope_id or not sig_req.document_id:
        return False

    from app.models.matters import Matter

    matter_result = await db.execute(select(Matter).where(Matter.id == sig_req.matter_id))
    matter = matter_result.scalar_one_or_none()
    if not matter:
        return False

    conn = await get_connection(db, firm_id=matter.firm_id)
    if not conn or not conn.access_token or not conn.external_account_id:
        logger.warning("docusign_download_no_connection")
        return False

    # Use token refresh to ensure valid token
    try:
        api = await _ensure_valid_token(db, conn)
    except Exception:
        logger.error("docusign_download_token_refresh_failed", exc_info=True)
        return False

    try:
        pdf_bytes = await api.download_document(sig_req.envelope_id)

        from app.services import storage_service

        storage_key = f"signed/{sig_req.matter_id}/{sig_req.envelope_id}.pdf"
        storage_service.upload_file(storage_key, pdf_bytes, "application/pdf")

        from app.models.document_versions import DocumentVersion

        doc_result = await db.execute(select(Document).where(Document.id == sig_req.document_id))
        doc = doc_result.scalar_one_or_none()
        if doc:
            new_version = doc.current_version + 1
            version = DocumentVersion(
                document_id=doc.id,
                version_number=new_version,
                storage_key=storage_key,
                size_bytes=len(pdf_bytes),
                uploaded_by=sig_req.sent_by,
            )
            db.add(version)
            doc.current_version = new_version
            sig_req.signed_document_id = doc.id
            await db.flush()

            logger.info(
                "docusign_signed_doc_registered",
                extra={
                    "doc_id": str(doc.id),
                    "version": new_version,
                    "envelope_id": sig_req.envelope_id,
                },
            )
            return True

    except Exception:
        logger.error("docusign_download_signed_doc_failed", exc_info=True)

    return False
