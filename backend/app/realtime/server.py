"""Socket.IO server — mounted alongside FastAPI for real-time matter updates.

Namespaces:
  /matters — one room per matter_id, JWT auth on connect

Events emitted (server → client):
  task_updated, document_uploaded, deadline_updated,
  communication_new, stakeholder_changed, event_new
"""

from __future__ import annotations

import logging
from typing import Any

import socketio

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Socket.IO server with Redis pub/sub manager
# ---------------------------------------------------------------------------

# Use Redis manager so multiple server processes share the same pub/sub
_manager_url = settings.redis_url

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=list(set(settings.backend_cors_origins + settings.cors_origins)),
    logger=settings.is_development,
    engineio_logger=False,
    client_manager=socketio.AsyncRedisManager(_manager_url),
)


def create_socketio_app():
    """Create the ASGI app wrapping Socket.IO, to be mounted on FastAPI."""
    return socketio.ASGIApp(sio, socketio_path="/socket.io")


# ---------------------------------------------------------------------------
# JWT authentication on connect
# ---------------------------------------------------------------------------


async def _authenticate_token(token: str) -> dict[str, Any] | None:
    """Validate a JWT token and return user info, or None on failure."""
    try:
        from app.core.security import verify_jwt

        payload = await verify_jwt(token)
        return {
            "sub": payload.sub,
            "email": payload.email,
        }
    except Exception:
        logger.warning("websocket_auth_failed", exc_info=True)
        return None


async def _get_user_stakeholder_matter_ids(auth_provider_id: str) -> list[str]:
    """Get all matter IDs this user is a stakeholder on (or firm member of)."""
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.firm_memberships import FirmMembership
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder
    from app.models.users import User

    async with async_session_factory() as session:
        # Find user
        result = await session.execute(
            select(User.id).where(User.auth_provider_id == auth_provider_id)
        )
        user_id = result.scalar_one_or_none()
        if user_id is None:
            return []

        # Get matters via stakeholder records
        stakeholder_matters = await session.execute(
            select(Stakeholder.matter_id).where(Stakeholder.user_id == user_id)
        )
        matter_ids = {str(row[0]) for row in stakeholder_matters.all()}

        # Also get matters via firm membership
        firm_result = await session.execute(
            select(FirmMembership.firm_id).where(FirmMembership.user_id == user_id)
        )
        firm_ids = [row[0] for row in firm_result.all()]

        if firm_ids:
            firm_matters = await session.execute(
                select(Matter.id).where(Matter.firm_id.in_(firm_ids))
            )
            for row in firm_matters.all():
                matter_ids.add(str(row[0]))

        return list(matter_ids)


# ---------------------------------------------------------------------------
# /matters namespace
# ---------------------------------------------------------------------------


class MatterNamespace(socketio.AsyncNamespace):
    """Handles connections to the /matters namespace.

    Clients connect with: { auth: { token: "Bearer <jwt>" } }
    Then emit 'join_matter' with { matter_id: "<uuid>" } to join a room.
    """

    async def on_connect(self, sid: str, environ: dict, auth: dict | None = None):
        """Authenticate the connection using JWT."""
        token = None

        # Extract token from auth dict
        if auth and isinstance(auth, dict):
            token = auth.get("token", "")
            if token.startswith("Bearer "):
                token = token[7:]

        if not token:
            logger.info("websocket_connect_rejected: no token", extra={"sid": sid})
            raise socketio.exceptions.ConnectionRefusedError("Authentication required")

        user_info = await _authenticate_token(token)
        if user_info is None:
            raise socketio.exceptions.ConnectionRefusedError("Invalid token")

        # Store user info in the session
        async with sio.session(sid, namespace="/matters") as session:
            session["user"] = user_info

        # Fetch authorized matter IDs
        authorized_matters = await _get_user_stakeholder_matter_ids(user_info["sub"])

        async with sio.session(sid, namespace="/matters") as session:
            session["authorized_matters"] = set(authorized_matters)

        logger.info(
            "websocket_connected",
            extra={
                "sid": sid,
                "email": user_info["email"],
                "authorized_matter_count": len(authorized_matters),
            },
        )

    async def on_disconnect(self, sid: str):
        logger.info("websocket_disconnected", extra={"sid": sid})

    async def on_join_matter(self, sid: str, data: dict):
        """Join a matter room. Validates the user is authorized for this matter."""
        matter_id = data.get("matter_id", "")

        async with sio.session(sid, namespace="/matters") as session:
            authorized = session.get("authorized_matters", set())

        if matter_id not in authorized:
            await sio.emit(
                "error",
                {"message": "Not authorized for this matter"},
                to=sid,
                namespace="/matters",
            )
            return

        sio.enter_room(sid, f"matter:{matter_id}", namespace="/matters")
        await sio.emit(
            "joined_matter",
            {"matter_id": matter_id},
            to=sid,
            namespace="/matters",
        )

        logger.info(
            "websocket_joined_matter",
            extra={"sid": sid, "matter_id": matter_id},
        )

    async def on_leave_matter(self, sid: str, data: dict):
        """Leave a matter room."""
        matter_id = data.get("matter_id", "")
        sio.leave_room(sid, f"matter:{matter_id}", namespace="/matters")

        logger.info(
            "websocket_left_matter",
            extra={"sid": sid, "matter_id": matter_id},
        )


# Register the namespace
sio.register_namespace(MatterNamespace("/matters"))


# ---------------------------------------------------------------------------
# Broadcast helpers (called from EventLogger / services)
# ---------------------------------------------------------------------------


async def broadcast_to_matter(matter_id: str, event: str, data: dict[str, Any]) -> None:
    """Emit a Socket.IO event to all clients in a matter room."""
    try:
        await sio.emit(
            event,
            data,
            room=f"matter:{matter_id}",
            namespace="/matters",
        )
        logger.debug(
            "websocket_broadcast",
            extra={"matter_id": matter_id, "event": event},
        )
    except Exception:
        # WebSocket broadcast failures should never break the main flow
        logger.warning("websocket_broadcast_failed", exc_info=True)
