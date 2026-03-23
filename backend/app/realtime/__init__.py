"""Real-time WebSocket module — Socket.IO server with Redis pub/sub."""

from app.realtime.server import create_socketio_app, sio

__all__ = ["create_socketio_app", "sio"]
