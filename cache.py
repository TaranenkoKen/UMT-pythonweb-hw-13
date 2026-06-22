import redis.asyncio as aioredis
import json
from typing import Optional
from config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return a shared async Redis client, creating it on first call.

    Returns:
        An async Redis client connected to ``settings.REDIS_URL``.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def cache_user(email: str, user_data: dict, ttl: int = 900) -> None:
    """Store serialised user data in Redis.

    Args:
        email: The user's email address used as the cache key.
        user_data: A dict representation of the user to cache.
        ttl: Time-to-live in seconds (default 15 minutes).
    """
    r = await get_redis()
    await r.setex(f"user:{email}", ttl, json.dumps(user_data))


async def get_cached_user(email: str) -> Optional[dict]:
    """Retrieve cached user data from Redis.

    Args:
        email: The user's email address.

    Returns:
        The cached user dict, or ``None`` if the key is absent / expired.
    """
    r = await get_redis()
    data = await r.get(f"user:{email}")
    if data:
        return json.loads(data)
    return None


async def invalidate_user_cache(email: str) -> None:
    """Remove a user's cached entry from Redis.

    Args:
        email: The user's email address whose cache entry should be deleted.
    """
    r = await get_redis()
    await r.delete(f"user:{email}")
