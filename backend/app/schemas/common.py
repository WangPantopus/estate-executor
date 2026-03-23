"""Common schemas shared across domains."""

from __future__ import annotations

from typing import Any

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "total": 42,
                    "page": 1,
                    "per_page": 50,
                    "total_pages": 1,
                }
            ]
        },
    )

    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)


class PaginationParams:
    """FastAPI Query dependency for pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    ) -> None:
        self.page = page
        self.per_page = per_page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class ErrorDetail(BaseModel):
    """Structured error detail."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "code": "validation_error",
                    "message": "Field is required",
                    "field": "title",
                }
            ]
        },
    )

    code: str
    message: str
    field: str | None = None


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "data": {"id": "123"},
                    "meta": None,
                    "errors": None,
                }
            ]
        },
    )

    data: Any
    meta: PaginationMeta | None = None
    errors: list[ErrorDetail] | None = None
