from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])

# Domain routers will be added as they are implemented:
# api_router.include_router(firms_router, prefix="/firms", tags=["firms"])
# api_router.include_router(matters_router, ...)
# etc.
