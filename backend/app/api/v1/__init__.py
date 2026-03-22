from fastapi import APIRouter

from app.api.v1.assets import router as assets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.entities import entity_map_router
from app.api.v1.entities import router as entities_router
from app.api.v1.firms import router as firms_router
from app.api.v1.health import router as health_router
from app.api.v1.matters import router as matters_router
from app.api.v1.stakeholders import router as stakeholders_router
from app.api.v1.tasks import router as tasks_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(firms_router, prefix="/firms", tags=["firms"])
api_router.include_router(matters_router, prefix="/firms/{firm_id}/matters", tags=["matters"])
api_router.include_router(
    stakeholders_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/stakeholders",
    tags=["stakeholders"],
)
api_router.include_router(
    tasks_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/tasks",
    tags=["tasks"],
)
api_router.include_router(
    assets_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/assets",
    tags=["assets"],
)
api_router.include_router(
    entities_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/entities",
    tags=["entities"],
)
api_router.include_router(
    entity_map_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/entity-map",
    tags=["entities"],
)
