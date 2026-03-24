"""S3/MinIO storage service — presigned URLs for upload and download."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from botocore.config import Config as BotoConfig

from app.core.config import settings

logger = logging.getLogger(__name__)

_PRESIGN_EXPIRY = 900  # 15 minutes


def _get_s3_client() -> Any:
    """Get or create an S3 client configured for the current environment.

    In development, connects to MinIO; in production, uses AWS S3.
    """
    import boto3

    client_kwargs: dict[str, Any] = {
        "region_name": settings.aws_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "config": BotoConfig(signature_version="s3v4"),
    }
    # MinIO / local S3-compatible endpoint
    if settings.s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url

    return boto3.client("s3", **client_kwargs)


def generate_upload_url(
    *,
    firm_id: uuid.UUID,
    matter_id: uuid.UUID,
    filename: str,
    mime_type: str,
) -> tuple[str, str]:
    """Generate a presigned PUT URL for direct browser upload.

    Returns (upload_url, storage_key).
    storage_key format: firms/{firm_id}/matters/{matter_id}/documents/{uuid}/{filename}
    """
    doc_uuid = uuid.uuid4()
    storage_key = f"firms/{firm_id}/matters/{matter_id}/documents/{doc_uuid}/{filename}"

    client = _get_s3_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.aws_s3_bucket,
            "Key": storage_key,
            "ContentType": mime_type,
        },
        ExpiresIn=_PRESIGN_EXPIRY,
    )

    logger.info(
        "presigned_upload_url_generated",
        extra={
            "storage_key": storage_key,
            "mime_type": mime_type,
            "expires_in": _PRESIGN_EXPIRY,
        },
    )

    return upload_url, storage_key


def generate_presigned_put_url(*, storage_key: str, content_type: str) -> str:
    """Generate a presigned PUT URL for a specific storage key."""
    client = _get_s3_client()
    url: str = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.aws_s3_bucket,
            "Key": storage_key,
            "ContentType": content_type,
        },
        ExpiresIn=_PRESIGN_EXPIRY,
    )
    return url


def download_file(storage_key: str) -> bytes:
    """Download a file from S3/MinIO and return its bytes."""
    client = _get_s3_client()
    resp = client.get_object(Bucket=settings.aws_s3_bucket, Key=storage_key)
    return resp["Body"].read()  # type: ignore[no-any-return]


def upload_file(storage_key: str, data: bytes, content_type: str) -> None:
    """Upload bytes to S3/MinIO."""
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.aws_s3_bucket,
        Key=storage_key,
        Body=data,
        ContentType=content_type,
    )
    logger.info("s3_object_uploaded", extra={"storage_key": storage_key})


def generate_download_url(*, storage_key: str) -> str:
    """Generate a presigned GET URL for document download (15-minute expiry)."""
    client = _get_s3_client()
    return client.generate_presigned_url(  # type: ignore[no-any-return]
        "get_object",
        Params={
            "Bucket": settings.aws_s3_bucket,
            "Key": storage_key,
        },
        ExpiresIn=_PRESIGN_EXPIRY,
    )


def delete_object(*, storage_key: str) -> None:
    """Delete an object from S3/MinIO."""
    client = _get_s3_client()
    client.delete_object(
        Bucket=settings.aws_s3_bucket,
        Key=storage_key,
    )
    logger.info("s3_object_deleted", extra={"storage_key": storage_key})
