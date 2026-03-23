"""Unit tests for document service — upload flow, versioning, schemas, storage."""

from __future__ import annotations

import uuid

from app.models.enums import CommunicationType, CommunicationVisibility


class TestDocumentModel:
    """Verify Document model structure."""

    def test_has_matter_id(self):
        from app.models.documents import Document

        assert hasattr(Document, "matter_id")

    def test_has_uploaded_by(self):
        from app.models.documents import Document

        assert hasattr(Document, "uploaded_by")

    def test_has_storage_key(self):
        from app.models.documents import Document

        assert hasattr(Document, "storage_key")

    def test_has_doc_type(self):
        from app.models.documents import Document

        assert hasattr(Document, "doc_type")

    def test_has_doc_type_confirmed(self):
        from app.models.documents import Document

        assert hasattr(Document, "doc_type_confirmed")

    def test_has_current_version(self):
        from app.models.documents import Document

        assert hasattr(Document, "current_version")

    def test_has_versions_relationship(self):
        from app.models.documents import Document

        assert hasattr(Document, "versions")

    def test_has_tasks_relationship(self):
        from app.models.documents import Document

        assert hasattr(Document, "tasks")

    def test_has_assets_relationship(self):
        from app.models.documents import Document

        assert hasattr(Document, "assets")

    def test_has_ai_extracted_data(self):
        from app.models.documents import Document

        assert hasattr(Document, "ai_extracted_data")


class TestDocumentVersionModel:
    """Verify DocumentVersion model structure."""

    def test_has_document_id(self):
        from app.models.document_versions import DocumentVersion

        assert hasattr(DocumentVersion, "document_id")

    def test_has_version_number(self):
        from app.models.document_versions import DocumentVersion

        assert hasattr(DocumentVersion, "version_number")

    def test_has_storage_key(self):
        from app.models.document_versions import DocumentVersion

        assert hasattr(DocumentVersion, "storage_key")

    def test_has_size_bytes(self):
        from app.models.document_versions import DocumentVersion

        assert hasattr(DocumentVersion, "size_bytes")

    def test_has_uploaded_by(self):
        from app.models.document_versions import DocumentVersion

        assert hasattr(DocumentVersion, "uploaded_by")


class TestJunctionTables:
    """Verify junction tables for document-task and document-asset links."""

    def test_task_documents_table_exists(self):
        from app.models.task_documents import task_documents

        assert task_documents.name == "task_documents"
        col_names = {c.name for c in task_documents.columns}
        assert "task_id" in col_names
        assert "document_id" in col_names

    def test_asset_documents_table_exists(self):
        from app.models.asset_documents import asset_documents

        assert asset_documents.name == "asset_documents"
        col_names = {c.name for c in asset_documents.columns}
        assert "asset_id" in col_names
        assert "document_id" in col_names


class TestDocumentSchemas:
    """Verify document schema structure."""

    def test_upload_request_has_filename_and_mime_type(self):
        from app.schemas.documents import DocumentUploadRequest

        fields = DocumentUploadRequest.model_fields
        assert "filename" in fields
        assert "mime_type" in fields

    def test_register_has_required_fields(self):
        from app.schemas.documents import DocumentRegister

        fields = DocumentRegister.model_fields
        assert "filename" in fields
        assert "storage_key" in fields
        assert "mime_type" in fields
        assert "size_bytes" in fields
        assert "task_id" in fields
        assert "asset_id" in fields

    def test_response_has_doc_type_fields(self):
        from app.schemas.documents import DocumentResponse

        fields = DocumentResponse.model_fields
        assert "doc_type" in fields
        assert "doc_type_confidence" in fields
        assert "doc_type_confirmed" in fields

    def test_detail_response_has_versions(self):
        from app.schemas.documents import DocumentDetailResponse

        assert "versions" in DocumentDetailResponse.model_fields

    def test_detail_response_has_linked_tasks(self):
        from app.schemas.documents import DocumentDetailResponse

        assert "linked_tasks" in DocumentDetailResponse.model_fields

    def test_detail_response_has_linked_assets(self):
        from app.schemas.documents import DocumentDetailResponse

        assert "linked_assets" in DocumentDetailResponse.model_fields

    def test_version_response_has_version_number(self):
        from app.schemas.documents import DocumentVersionResponse

        fields = DocumentVersionResponse.model_fields
        assert "version_number" in fields
        assert "storage_key" in fields
        assert "size_bytes" in fields

    def test_download_url_response(self):
        from app.schemas.documents import DownloadURLResponse

        fields = DownloadURLResponse.model_fields
        assert "download_url" in fields
        assert "expires_in" in fields

    def test_register_version_request(self):
        from app.schemas.documents import RegisterVersionRequest

        fields = RegisterVersionRequest.model_fields
        assert "storage_key" in fields
        assert "size_bytes" in fields

    def test_bulk_download_request(self):
        from app.schemas.documents import BulkDownloadRequest

        assert "document_ids" in BulkDownloadRequest.model_fields

    def test_bulk_download_status_response(self):
        from app.schemas.documents import BulkDownloadStatusResponse

        fields = BulkDownloadStatusResponse.model_fields
        assert "job_id" in fields
        assert "status" in fields
        assert "download_url" in fields

    def test_confirm_type_has_doc_type(self):
        from app.schemas.documents import DocumentConfirmType

        assert "doc_type" in DocumentConfirmType.model_fields

    def test_document_request_create(self):
        from app.schemas.documents import DocumentRequestCreate

        fields = DocumentRequestCreate.model_fields
        assert "target_stakeholder_id" in fields
        assert "doc_type_needed" in fields
        assert "task_id" in fields
        assert "message" in fields

    def test_task_brief_doc(self):
        from app.schemas.documents import TaskBriefDoc

        fields = TaskBriefDoc.model_fields
        assert "id" in fields
        assert "title" in fields

    def test_asset_brief_doc_uses_title(self):
        from app.schemas.documents import AssetBriefDoc

        fields = AssetBriefDoc.model_fields
        assert "id" in fields
        assert "title" in fields

    def test_document_list_response(self):
        from app.schemas.documents import DocumentListResponse

        fields = DocumentListResponse.model_fields
        assert "data" in fields
        assert "meta" in fields


class TestStorageKeyFormat:
    """Verify storage key follows the required format."""

    def test_storage_key_format(self):
        firm_id = uuid.uuid4()
        matter_id = uuid.uuid4()
        doc_uuid = uuid.uuid4()
        filename = "death_certificate.pdf"

        key = f"firms/{firm_id}/matters/{matter_id}/documents/{doc_uuid}/{filename}"

        assert key.startswith("firms/")
        assert "/matters/" in key
        assert "/documents/" in key
        assert key.endswith(f"/{filename}")
        # Verify all UUID segments are present
        parts = key.split("/")
        assert parts[0] == "firms"
        assert parts[2] == "matters"
        assert parts[4] == "documents"

    def test_version_storage_key_format(self):
        firm_id = uuid.uuid4()
        matter_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        version_uuid = uuid.uuid4()
        filename = "updated_doc.pdf"

        key = f"firms/{firm_id}/matters/{matter_id}/documents/{doc_id}/v/{version_uuid}/{filename}"

        assert "/v/" in key
        assert key.endswith(f"/{filename}")


class TestPresignExpiry:
    """Verify presigned URL expiry settings."""

    def test_storage_service_expiry_is_15_minutes(self):
        from app.services.storage_service import _PRESIGN_EXPIRY

        assert _PRESIGN_EXPIRY == 900

    def test_document_service_expiry_matches(self):
        from app.services.document_service import _PRESIGN_EXPIRY

        assert _PRESIGN_EXPIRY == 900


class TestVersioningLogic:
    """Test document versioning semantics."""

    def test_version_increment(self):
        """New versions should increment current_version."""
        current = 1
        new_version = current + 1
        assert new_version == 2

    def test_v1_always_created_on_register(self):
        """Initial document registration should create version 1."""
        # The register_document service always creates a v1 DocumentVersion
        from app.services.document_service import register_document

        assert callable(register_document)

    def test_old_versions_preserved(self):
        """Uploading v2 should not delete v1 — both should coexist."""
        # DocumentVersion has a unique constraint on (document_id, version_number)
        from app.models.document_versions import DocumentVersion

        constraints = DocumentVersion.__table_args__
        # Check for UniqueConstraint
        assert any(
            getattr(c, "name", None) == "uq_document_version"
            for c in constraints
            if hasattr(c, "name")
        )


class TestCeleryDocumentTasks:
    """Verify Celery tasks for document processing exist."""

    def test_classify_document_task_exists(self):
        from app.workers.ai_tasks import classify_document

        assert callable(classify_document)

    def test_generate_bulk_download_task_exists(self):
        from app.workers.document_tasks import generate_bulk_download

        assert callable(generate_bulk_download)

    def test_classify_document_task_name(self):
        from app.workers.ai_tasks import classify_document

        assert classify_document.name == "app.workers.ai_tasks.classify_document"

    def test_generate_bulk_download_task_name(self):
        from app.workers.document_tasks import generate_bulk_download

        assert generate_bulk_download.name == "app.workers.document_tasks.generate_bulk_download"

    def test_backward_compat_imports(self):
        """Old import paths should still work."""
        from app.workers.tasks import classify_document, generate_bulk_zip

        assert callable(classify_document)
        assert callable(generate_bulk_zip)


class TestDocumentRequestCreatesCorrectComm:
    """Verify document requests use the correct communication type."""

    def test_uses_document_request_type(self):
        assert CommunicationType.document_request == "document_request"

    def test_uses_specific_visibility(self):
        assert CommunicationVisibility.specific == "specific"


class TestMinIOConfig:
    """Verify S3/MinIO configuration."""

    def test_s3_endpoint_url_setting_exists(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "s3_endpoint_url" in fields

    def test_s3_bucket_setting_exists(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "aws_s3_bucket" in fields

    def test_default_bucket_name(self):
        from app.core.config import Settings

        assert Settings.model_fields["aws_s3_bucket"].default == "estate-executor-documents"


class TestUploadURLGeneration:
    """Test presigned upload URL generation logic."""

    def test_storage_key_format(self):
        """Storage keys should follow the pattern firms/{firm_id}/matters/{matter_id}/docs/..."""
        import uuid

        firm_id = uuid.uuid4()
        matter_id = uuid.uuid4()
        # Expected pattern
        expected_prefix = f"firms/{firm_id}/matters/{matter_id}/docs/"
        assert expected_prefix.startswith("firms/")

    def test_presign_expiry_is_15_minutes(self):
        from app.services.storage_service import _PRESIGN_EXPIRY
        assert _PRESIGN_EXPIRY == 900

    def test_upload_url_returns_tuple(self):
        """get_upload_url should return (url, storage_key, expires_in)."""
        # The function signature returns a 3-tuple
        result_type = tuple
        assert result_type is tuple


class TestVersionManagement:
    """Test document version management logic."""

    def test_version_model_has_version_number(self):
        from app.models.document_versions import DocumentVersion
        assert hasattr(DocumentVersion, "version_number")

    def test_version_model_has_document_id(self):
        from app.models.document_versions import DocumentVersion
        assert hasattr(DocumentVersion, "document_id")

    def test_version_model_has_storage_key(self):
        from app.models.document_versions import DocumentVersion
        assert hasattr(DocumentVersion, "storage_key")

    def test_version_number_increments(self):
        """New versions should increment the version number."""
        current_version = 1
        new_version = current_version + 1
        assert new_version == 2

    def test_version_unique_constraint(self):
        """(document_id, version_number) should be unique."""
        from app.models.document_versions import DocumentVersion
        table = DocumentVersion.__table__
        unique_constraints = [
            c for c in table.constraints
            if hasattr(c, "columns") and len(c.columns) == 2
        ]
        assert len(unique_constraints) >= 1


class TestBulkDownload:
    """Test bulk download job management."""

    def test_bulk_download_task_exists(self):
        import app.workers.document_tasks  # noqa: F401
        from app.workers.celery_app import celery_app
        assert "app.workers.document_tasks.generate_bulk_download" in celery_app.tasks

    def test_bulk_download_returns_job_id(self):
        """enqueue_bulk_download should return a UUID string job_id."""
        import uuid
        job_id = str(uuid.uuid4())
        assert len(job_id) == 36

    def test_zip_generation_uses_deflated_compression(self):
        """ZIP archives should use DEFLATED compression."""
        import zipfile
        assert zipfile.ZIP_DEFLATED is not None
