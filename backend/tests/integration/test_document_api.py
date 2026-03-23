"""Integration tests: document API — upload flow with mock S3."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
class TestDocumentUpload:
    @patch("app.services.document_service.get_upload_url")
    async def test_get_upload_url_returns_200(self, mock_upload, client, firm_id, matter_id):
        mock_upload.return_value = ("https://s3.example.com/presigned", "firms/key.pdf", 900)
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/documents/upload-url",
            json={"filename": "will.pdf", "mime_type": "application/pdf"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_url" in data
        assert "storage_key" in data
        assert data["expires_in"] == 900

    async def test_upload_url_missing_filename_returns_422(self, client, firm_id, matter_id):
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/documents/upload-url",
            json={"mime_type": "application/pdf"},
        )
        assert resp.status_code == 422

    async def test_upload_url_missing_mime_returns_422(self, client, firm_id, matter_id):
        resp = await client.post(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/documents/upload-url",
            json={"filename": "test.pdf"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestDocumentListing:
    @patch("app.services.document_service.list_documents")
    async def test_list_documents_returns_200(self, mock_list, client, firm_id, matter_id):
        mock_list.return_value = ([], 0)
        resp = await client.get(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/documents"
        )
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 0


@pytest.mark.asyncio
class TestDocumentNotFound:
    @patch("app.services.document_service.get_document")
    async def test_get_nonexistent_doc_returns_404(
        self, mock_get, client, firm_id, matter_id
    ):
        from app.core.exceptions import NotFoundError

        mock_get.side_effect = NotFoundError(detail="Document not found")
        resp = await client.get(
            f"/api/v1/firms/{firm_id}/matters/{matter_id}/documents/{uuid.uuid4()}"
        )
        assert resp.status_code == 404
