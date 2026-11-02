"""Quantum Flow Technologies — Redis Connection & Health Diagnostics."""

import inspect
import logging

from redis.asyncio import Redis, from_url

from services.api.app.core.config import settings

logger = logging.getLogger(__name__)


async def check_redis_health() -> tuple[bool, str]:
    """Verify connectivity to Redis broker by executing a PING command.

    Returns sanitized status messages to prevent connection URL disclosure.
    """
    client: Redis | None = None
    try:
        client = from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        assert client is not None
        ping_res = client.ping()
        pong = await ping_res if inspect.isawaitable(ping_res) else ping_res
        if pong is True:
            return True, "connected"
        return False, "unexpected ping response"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return False, "Redis connection unavailable"
    finally:
        if client is not None:
            await client.aclose()


async def close_redis_client() -> None:
    """Close any shared Redis connections upon application shutdown."""
    # Scaffolded for persistent Redis clients used across background workers
    pass
