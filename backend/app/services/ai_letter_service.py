"""AI letter drafting service — generates formal estate administration letters.

Gathers matter context, asset details, and executor/trustee info, then uses
Claude to draft professional notification and claim letters.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.events import event_logger
from app.models.ai_usage_logs import AIUsageLog
from app.models.assets import Asset
from app.models.enums import ActorType, StakeholderRole
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.prompts import get_prompt_version
from app.schemas.ai import AILetterDraftResponse
from app.services.ai_rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"


def _mask_account_number(encrypted: bytes | None) -> str | None:
    """Decrypt and mask an account number — only show last 4 characters."""
    if encrypted is None:
        return None
    try:
        from app.core.security import decrypt_field

        plaintext = decrypt_field(encrypted)
        if len(plaintext) <= 4:
            return "****"
        return "****" + plaintext[-4:]
    except Exception:
        logger.warning("Failed to decrypt account number for letter draft")
        return "****"


_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0

# ─── Letter type definitions ─────────────────────────────────────────────────

LETTER_TYPES: dict[str, dict[str, str]] = {
    "institution_notification": {
        "label": "Institution Death Notification",
        "description": "Notify a financial institution (bank, brokerage, insurance company) of the account holder's death",
        "purpose": "Request account freeze, obtain date-of-death balance, and initiate transfer/distribution process",
    },
    "creditor_notification": {
        "label": "Creditor Notification",
        "description": "Formal notice to a creditor regarding the decedent's estate",
        "purpose": "Notify of death, request claim submission, and provide estate contact information",
    },
    "beneficiary_notification": {
        "label": "Beneficiary Notification",
        "description": "Notify a beneficiary of their interest in the estate",
        "purpose": "Inform beneficiary of their interest, outline distribution timeline, and provide contact information",
    },
    "government_agency": {
        "label": "Government Agency Notification",
        "description": "Notify a government agency (SSA, DMV, IRS) of the death",
        "purpose": "Report death to the relevant agency and request appropriate action (benefit cessation, license cancellation, etc.)",
    },
    "subscription_cancellation": {
        "label": "Subscription Cancellation",
        "description": "Cancel a recurring subscription or service in the decedent's name",
        "purpose": "Cancel service, request final billing statement, and redirect any refunds to the estate",
    },
    "insurance_claim": {
        "label": "Insurance Claim Initiation",
        "description": "Initiate a life insurance death benefit claim",
        "purpose": "Submit formal claim for death benefit, provide required documentation references, and request claim forms",
    },
}


def _build_system_prompt() -> str:
    """Build the system prompt for letter drafting."""
    return (
        "You are drafting a formal letter for estate administration. "
        "Write in a professional, formal tone appropriate for legal correspondence. "
        "Include standard legal language appropriate for the letter type. "
        "IMPORTANT: Never include full Social Security numbers, full account numbers, "
        "or other sensitive personally identifiable information. Only use masked/partial numbers."
    )


def _build_user_prompt(
    *,
    letter_type: str,
    letter_config: dict[str, str],
    decedent_name: str,
    date_of_death: str | None,
    estate_type: str,
    jurisdiction: str,
    executor_name: str | None,
    executor_title: str,
    institution: str | None,
    account_number_masked: str | None,
    asset_title: str | None,
    asset_type: str | None,
    asset_value: str | None,
    court_case_number: str | None,
) -> str:
    """Build the user prompt with all context for letter drafting."""
    context_lines: list[str] = []

    context_lines.append(f"Letter type: {letter_config['label']}")
    context_lines.append(f"Purpose: {letter_config['purpose']}")
    context_lines.append("")
    context_lines.append("Estate details:")
    context_lines.append(f"  Decedent name: {decedent_name}")
    if date_of_death:
        context_lines.append(f"  Date of death: {date_of_death}")
    context_lines.append(f"  Estate type: {estate_type}")
    context_lines.append(f"  Jurisdiction: {jurisdiction}")

    if executor_name:
        context_lines.append(f"  {executor_title}: {executor_name}")
    if court_case_number:
        context_lines.append(f"  Court case number: {court_case_number}")

    if institution or asset_title:
        context_lines.append("")
        context_lines.append("Asset/Account details:")
        if institution:
            context_lines.append(f"  Institution: {institution}")
        if asset_title:
            context_lines.append(f"  Asset: {asset_title}")
        if asset_type:
            context_lines.append(f"  Asset type: {asset_type}")
        if account_number_masked:
            context_lines.append(f"  Account number (masked): {account_number_masked}")
        if asset_value:
            context_lines.append(f"  Estimated value: {asset_value}")

    context = "\n".join(context_lines)

    return f"""Draft a formal {letter_config['label'].lower()} letter based on the following details:

{context}

Requirements:
- Professional, formal tone appropriate for legal correspondence
- Include a clear subject line
- Include appropriate salutation and closing
- Reference the decedent by full name
- Reference the date of death if available
- If an institution is specified, address it as the recipient
- Include the {executor_title}'s name and authority
- Include standard legal language for this type of letter
- Never include full account numbers or SSN — only use masked versions
- Keep the letter concise but complete (typically 1-2 pages)

Generate the letter now."""


def _build_tool_schema() -> dict[str, Any]:
    """Build the tool-use schema for structured letter output."""
    return {
        "name": "draft_letter",
        "description": "Generate a formal estate administration letter",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Subject line for the letter",
                },
                "body": {
                    "type": "string",
                    "description": "Full letter body including salutation, paragraphs, and closing. Use newlines for paragraph breaks.",
                },
                "recipient_institution": {
                    "type": "string",
                    "description": "Name of the recipient institution or agency",
                },
            },
            "required": ["subject", "body", "recipient_institution"],
        },
    }


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of a Claude API call in USD."""
    input_cost = (input_tokens / 1_000_000) * _INPUT_COST_PER_M
    output_cost = (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
    return round(input_cost + output_cost, 6)


def _call_claude(user_prompt: str) -> tuple[dict[str, Any], int, int]:
    """Call Claude API for letter drafting. Returns (result, input_tokens, output_tokens)."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool = _build_tool_schema()

    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=_build_system_prompt(),
        tools=[tool],
        tool_choice={"type": "tool", "name": "draft_letter"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_result: dict[str, Any] | None = None
    for block in response.content:
        if block.type == "tool_use":
            tool_result = block.input  # type: ignore[assignment]
            break

    if tool_result is None:
        raise ValueError("Claude did not return a tool_use response for letter drafting")

    return tool_result, response.usage.input_tokens, response.usage.output_tokens


async def _log_ai_usage(
    db: AsyncSession,
    *,
    firm_id: UUID,
    matter_id: UUID,
    document_id: UUID | None = None,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    cost_estimate: float,
    status: str = "success",
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log AI API usage to the ai_usage_logs table."""
    log_entry = AIUsageLog(
        firm_id=firm_id,
        matter_id=matter_id,
        document_id=document_id,
        operation=operation,
        model=_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate_usd=cost_estimate,
        status=status,
        error_message=error_message,
        metadata_=metadata or {},
    )
    db.add(log_entry)
    await db.flush()


async def _get_executor_info(
    db: AsyncSession, matter_id: UUID
) -> tuple[str | None, str]:
    """Find the executor/trustee stakeholder for the matter.

    Returns (name, title) where title is 'Executor', 'Trustee', etc.
    """
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.matter_id == matter_id,
            Stakeholder.role == StakeholderRole.executor_trustee,
        )
    )
    executor = result.scalars().first()
    if executor:
        return executor.full_name, "Executor/Trustee"

    # Fall back to matter_admin
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.matter_id == matter_id,
            Stakeholder.role == StakeholderRole.matter_admin,
        )
    )
    admin = result.scalars().first()
    if admin:
        return admin.full_name, "Estate Administrator"

    return None, "Personal Representative"


async def draft_letter(
    db: AsyncSession,
    *,
    matter_id: UUID,
    asset_id: UUID,
    letter_type: str,
) -> AILetterDraftResponse:
    """Draft a formal estate administration letter.

    1. Validates letter_type and asset
    2. Gathers matter context and executor info
    3. Calls Claude to generate the letter
    4. Logs usage and audit event
    """
    # Validate letter type
    if letter_type not in LETTER_TYPES:
        raise ValueError(
            f"Unknown letter type '{letter_type}'. "
            f"Valid types: {', '.join(sorted(LETTER_TYPES.keys()))}"
        )
    letter_config = LETTER_TYPES[letter_type]

    # Fetch asset
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.matter_id == matter_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise ValueError(f"Asset {asset_id} not found in matter {matter_id}")

    # Fetch matter
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise ValueError(f"Matter {matter_id} not found")

    # Check rate limits
    check_rate_limit(firm_id=matter.firm_id, matter_id=matter.id)

    # Get executor info
    executor_name, executor_title = await _get_executor_info(db, matter_id)

    # Get court case number from settings if available
    court_case_number = (matter.settings or {}).get("court_case_number")

    # Build masked account info
    account_masked = _mask_account_number(asset.account_number_encrypted)

    # Format date of death
    date_of_death_str = (
        matter.date_of_death.strftime("%B %d, %Y") if matter.date_of_death else None
    )

    # Format estate type
    estate_type_display = (
        matter.estate_type.value.replace("_", " ").title()
        if hasattr(matter.estate_type, "value")
        else str(matter.estate_type)
    )

    # Format asset value
    asset_value_str = None
    if asset.current_estimated_value is not None:
        asset_value_str = f"${asset.current_estimated_value:,.2f}"
    elif asset.date_of_death_value is not None:
        asset_value_str = f"${asset.date_of_death_value:,.2f}"

    # Build prompt
    user_prompt = _build_user_prompt(
        letter_type=letter_type,
        letter_config=letter_config,
        decedent_name=matter.decedent_name,
        date_of_death=date_of_death_str,
        estate_type=estate_type_display,
        jurisdiction=matter.jurisdiction_state,
        executor_name=executor_name,
        executor_title=executor_title,
        institution=asset.institution,
        account_number_masked=account_masked,
        asset_title=asset.title,
        asset_type=asset.asset_type.value.replace("_", " ").title() if hasattr(asset.asset_type, "value") else str(asset.asset_type),
        asset_value=asset_value_str,
        court_case_number=court_case_number,
    )

    # Call Claude
    try:
        parsed_result, input_tokens, output_tokens = _call_claude(user_prompt)
    except Exception as exc:
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            operation="draft_letter",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message=str(exc),
            metadata={"letter_type": letter_type, "asset_id": str(asset_id)},
        )
        raise

    cost_estimate = _estimate_cost(input_tokens, output_tokens)

    response = AILetterDraftResponse(
        subject=parsed_result["subject"],
        body=parsed_result["body"],
        recipient_institution=parsed_result["recipient_institution"],
    )

    # Log AI usage
    await _log_ai_usage(
        db,
        firm_id=matter.firm_id,
        matter_id=matter.id,
        operation="draft_letter",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost_estimate,
        metadata={
            "letter_type": letter_type,
            "asset_id": str(asset_id),
            "recipient": response.recipient_institution,
        },
    )

    # Log audit event
    await event_logger.log(
        db,
        matter_id=matter.id,
        actor_id=None,
        actor_type=ActorType.ai,
        entity_type="asset",
        entity_id=asset.id,
        action="letter_drafted",
        metadata={
            "letter_type": letter_type,
            "recipient_institution": response.recipient_institution,
            "subject": response.subject,
            "model": _MODEL,
            "prompt_version": get_prompt_version("draft_letter"),
        },
    )

    logger.info(
        "letter_drafted",
        extra={
            "matter_id": str(matter_id),
            "asset_id": str(asset_id),
            "letter_type": letter_type,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_estimate_usd": cost_estimate,
        },
    )

    return response
