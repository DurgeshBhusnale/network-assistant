"""Redis client (queue, rate limits)."""

from redis.asyncio import Redis

from app.core.config import Settings


def create_redis(settings: Settings) -> "Redis":
    client: Redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    return client


async def ping_redis(client: "Redis") -> None:
    await client.ping()
