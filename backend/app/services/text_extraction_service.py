"""Text extraction service — extracts text from PDF, image, and DOCX documents.

Uses PyMuPDF (fitz) for PDFs, pytesseract for OCR on images, and python-docx
for Word documents. Extracted text is truncated to 5000 tokens to manage
Claude API costs.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Approximate token limit (1 token ≈ 4 chars for English text)
_MAX_TOKENS = 5000
_MAX_CHARS = _MAX_TOKENS * 4

# MIME type groups
_PDF_TYPES = {"application/pdf"}
_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
    "image/gif",
    "image/webp",
}
_DOCX_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


def _get_s3_client() -> Any:
    """Lazy import to avoid circular deps at module level."""
    from app.services.storage_service import _get_s3_client as get_client

    return get_client()


def _download_file(storage_key: str) -> bytes:
    """Download a file from S3/MinIO and return raw bytes."""
    client = _get_s3_client()
    response = client.get_object(
        Bucket=settings.aws_s3_bucket,
        Key=storage_key,
    )
    return response["Body"].read()  # type: ignore[no-any-return]


def _truncate_text(text: str) -> str:
    """Truncate text to approximately _MAX_TOKENS tokens."""
    if len(text) <= _MAX_CHARS:
        return text
    # Truncate at char boundary, then trim to last complete word
    truncated = text[:_MAX_CHARS]
    last_space = truncated.rfind(" ")
    if last_space > _MAX_CHARS * 0.8:
        truncated = truncated[:last_space]
    return truncated + "\n[... text truncated for processing ...]"


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    import fitz

    text_parts: list[str] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text_parts.append(page_text)
            # Early exit if we already have enough text
            if len("\n".join(text_parts)) > _MAX_CHARS:
                break
    return "\n".join(text_parts)


def _extract_image(file_bytes: bytes) -> str:
    """Extract text from an image using Tesseract OCR."""
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(image)  # type: ignore[no-any-return]


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    import docx

    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text(storage_key: str, mime_type: str) -> str:
    """Extract text from a document stored in S3.

    Args:
        storage_key: S3 key for the document.
        mime_type: MIME type of the document.

    Returns:
        Extracted text, truncated to ~5000 tokens. Returns empty string on failure.
    """
    try:
        file_bytes = _download_file(storage_key)
    except Exception:
        logger.exception(
            "text_extraction_download_failed",
            extra={"storage_key": storage_key},
        )
        return ""

    try:
        if mime_type in _PDF_TYPES:
            raw_text = _extract_pdf(file_bytes)
        elif mime_type in _IMAGE_TYPES:
            raw_text = _extract_image(file_bytes)
        elif mime_type in _DOCX_TYPES:
            raw_text = _extract_docx(file_bytes)
        else:
            logger.warning(
                "text_extraction_unsupported_mime_type",
                extra={"mime_type": mime_type, "storage_key": storage_key},
            )
            return ""
    except Exception:
        logger.exception(
            "text_extraction_failed",
            extra={"storage_key": storage_key, "mime_type": mime_type},
        )
        return ""

    text = raw_text.strip()
    if not text:
        logger.warning(
            "text_extraction_empty_result",
            extra={"storage_key": storage_key, "mime_type": mime_type},
        )
        return ""

    truncated = _truncate_text(text)
    logger.info(
        "text_extraction_success",
        extra={
            "storage_key": storage_key,
            "mime_type": mime_type,
            "raw_chars": len(text),
            "truncated_chars": len(truncated),
        },
    )
    return truncated
