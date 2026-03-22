from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)
from app.core.middleware import (
    ExceptionHandlerMiddleware,
    RequestLoggingMiddleware,
    TenantIsolationMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Startup
    settings.configure_logging()
    yield
    # Shutdown


def _rfc7807_response(status_code: int, title: str, detail: str, request_path: str) -> JSONResponse:
    """Build an RFC 7807 Problem Details JSON response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "type": "about:blank",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": request_path,
        },
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Estate Executor OS",
        description="Coordination Operating System for Estate Administration",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: last added = outermost) ---

    # CORS — applied first by FastAPI
    all_origins = list(set(settings.backend_cors_origins + settings.cors_origins))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=all_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handler (outermost custom middleware — catches everything)
    app.add_middleware(ExceptionHandlerMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Tenant isolation
    app.add_middleware(TenantIsolationMiddleware)

    # --- Exception handlers for known HTTP exceptions ---

    @app.exception_handler(UnauthorizedError)
    async def _unauthorized(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Unauthorized", exc.detail, request.url.path)

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Not Found", exc.detail, request.url.path)

    @app.exception_handler(PermissionDeniedError)
    async def _forbidden(request: Request, exc: PermissionDeniedError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Forbidden", exc.detail, request.url.path)

    @app.exception_handler(ConflictError)
    async def _conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Conflict", exc.detail, request.url.path)

    @app.exception_handler(ValidationError)
    async def _validation(request: Request, exc: ValidationError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Validation Error", exc.detail, request.url.path)

    @app.exception_handler(RateLimitError)
    async def _rate_limit(request: Request, exc: RateLimitError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Too Many Requests", exc.detail, request.url.path)

    # --- Routes ---

    from app.api.v1 import api_router

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
