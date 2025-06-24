import redis.asyncio as aioredis
from app.config import settings

class RedisClient:
    def __init__(self):
        self._client = aioredis.from_url(settings.redis_url, decode_responses=True)
    async def get(self, key):
        return await self._client.get(key)
    async def set(self, key, value, ex=None):
        return await self._client.set(key, value, ex=ex)

def get_redis_client():
    return RedisClient() 