import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

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

# Background task handle for the realtime subscriber
_subscriber_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    global _subscriber_task
    # Startup
    settings.configure_logging()

    # Start the Redis pub/sub → Socket.IO bridge
    from app.realtime.subscriber import start_subscriber

    _subscriber_task = asyncio.create_task(start_subscriber())

    yield

    # Shutdown
    if _subscriber_task is not None:
        _subscriber_task.cancel()
        with suppress(asyncio.CancelledError):
            await _subscriber_task


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
    fastapi_app = FastAPI(
        title="Estate Executor OS",
        description="Coordination Operating System for Estate Administration",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: last added = outermost) ---

    # CORS — applied first by FastAPI
    all_origins = list(set(settings.backend_cors_origins + settings.cors_origins))
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=all_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handler (outermost custom middleware — catches everything)
    fastapi_app.add_middleware(ExceptionHandlerMiddleware)

    # Request logging
    fastapi_app.add_middleware(RequestLoggingMiddleware)

    # Tenant isolation
    fastapi_app.add_middleware(TenantIsolationMiddleware)

    # --- Exception handlers for known HTTP exceptions ---

    @fastapi_app.exception_handler(UnauthorizedError)
    async def _unauthorized(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Unauthorized", exc.detail, request.url.path)

    @fastapi_app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Not Found", exc.detail, request.url.path)

    @fastapi_app.exception_handler(PermissionDeniedError)
    async def _forbidden(request: Request, exc: PermissionDeniedError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Forbidden", exc.detail, request.url.path)

    @fastapi_app.exception_handler(ConflictError)
    async def _conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Conflict", exc.detail, request.url.path)

    @fastapi_app.exception_handler(ValidationError)
    async def _validation(request: Request, exc: ValidationError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Validation Error", exc.detail, request.url.path)

    @fastapi_app.exception_handler(RateLimitError)
    async def _rate_limit(request: Request, exc: RateLimitError) -> JSONResponse:
        return _rfc7807_response(exc.status_code, "Too Many Requests", exc.detail, request.url.path)

    # --- Routes ---

    from app.api.v1 import api_router

    fastapi_app.include_router(api_router, prefix="/api/v1")

    # --- Mount Socket.IO ---

    from app.realtime import create_socketio_app

    socketio_asgi = create_socketio_app()
    fastapi_app.mount("/ws", socketio_asgi)

    return fastapi_app


app = create_app()
