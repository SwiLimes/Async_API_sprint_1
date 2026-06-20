import json
from typing import Any, Optional

from redis.asyncio import Redis

CACHE_EXPIRE_IN_SECONDS = 300


def build_cache_key(prefix: str, **params: Any) -> str:
    parts = [prefix]
    for name, value in sorted(params.items()):
        parts.append(f'{name}={value if value is not None else ""}')
    return ':'.join(parts)


class RedisCache:

    def __init__(
            self,
            redis: Redis,
            prefix: str,
            ttl: int = CACHE_EXPIRE_IN_SECONDS,
    ):
        self.redis = redis
        self.prefix = prefix
        self.ttl = ttl

    def key(self, **params: Any) -> str:
        return build_cache_key(self.prefix, **params)

    async def get_json(self, cache_key: str) -> Optional[Any]:
        data = await self.redis.get(cache_key)
        if not data:
            return None
        return json.loads(data)

    async def set_json(self, cache_key: str, value: Any) -> None:
        await self.redis.set(cache_key, json.dumps(value), ex=self.ttl)
