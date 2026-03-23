"""Redis pub/sub subscriber — bridges Redis events to Socket.IO broadcasts.

Runs as a background task within the Socket.IO server process.
Listens on the 'estate_executor:realtime' channel and emits events
to the appropriate matter rooms.
"""

from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_CHANNEL = "estate_executor:realtime"


async def start_subscriber() -> None:
    """Start the Redis pub/sub subscriber loop.

    Runs forever, reconnecting on failure with exponential backoff.
    Should be launched as an asyncio task during server startup.
    """
    from app.realtime.server import sio

    backoff = 1
    max_backoff = 30

    while True:
        try:
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(_CHANNEL)

            logger.info("realtime_subscriber_started", extra={"channel": _CHANNEL})
            backoff = 1  # Reset on successful connection

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                try:
                    payload = json.loads(message["data"])
                    matter_id = payload["matter_id"]
                    event = payload["event"]
                    data = payload["data"]

                    await sio.emit(
                        event,
                        data,
                        room=f"matter:{matter_id}",
                        namespace="/matters",
                    )
                except (json.JSONDecodeError, KeyError):
                    logger.warning(
                        "realtime_subscriber_bad_message",
                        extra={"data": message.get("data")},
                    )
                except Exception:
                    logger.warning("realtime_subscriber_emit_failed", exc_info=True)

        except asyncio.CancelledError:
            logger.info("realtime_subscriber_cancelled")
            break
        except Exception:
            logger.warning(
                "realtime_subscriber_connection_lost",
                extra={"backoff": backoff},
                exc_info=True,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
