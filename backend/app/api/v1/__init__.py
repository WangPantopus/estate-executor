from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.portal import router as portal_router
from app.api.v1.assets import router as assets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.communications import dispute_flag_router
from app.api.v1.communications import router as communications_router
from app.api.v1.deadlines import router as deadlines_router
from app.api.v1.distributions import router as distributions_router
from app.api.v1.documents import router as documents_router
from app.api.v1.entities import entity_map_router
from app.api.v1.entities import router as entities_router
from app.api.v1.events import router as events_router
from app.api.v1.firms import router as firms_router
from app.api.v1.health import router as health_router
from app.api.v1.matters import router as matters_router
from app.api.v1.reports import router as reports_router
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
api_router.include_router(
    deadlines_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/deadlines",
    tags=["deadlines"],
)
api_router.include_router(
    distributions_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/distributions",
    tags=["distributions"],
)
api_router.include_router(
    communications_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/communications",
    tags=["communications"],
)
api_router.include_router(
    dispute_flag_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/dispute-flag",
    tags=["communications"],
)
api_router.include_router(
    documents_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/documents",
    tags=["documents"],
)
api_router.include_router(
    events_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/events",
    tags=["events"],
)
api_router.include_router(
    reports_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/reports",
    tags=["reports"],
)
api_router.include_router(
    ai_router,
    prefix="/firms/{firm_id}/matters/{matter_id}/ai",
    tags=["ai"],
)
api_router.include_router(
    portal_router,
    prefix="/portal",
    tags=["portal"],
)
