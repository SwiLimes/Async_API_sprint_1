import json
from typing import Optional, Any, TypeVar, Type
from pydantic import BaseModel
from redis.asyncio import Redis
from elasticsearch import AsyncElasticsearch
from core.config import CACHE_EXPIRE_IN_SECONDS

T = TypeVar('T', bound=BaseModel)

LIST_CACHE_PATTERNS = {
    'movies': ['films:list:*', 'films:search:*'],
    'genres': ['genres:list:*'],
    'persons': ['persons:list:*'],
}


class Cache:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_model(self, key: str, model: Type[T]) -> Optional[T]:
        data = await self.redis.get(key)
        if not data:
            return None
        return model.parse_raw(data)

    async def set_model(self, key: str, model: BaseModel) -> None:
        await self.redis.set(key, model.json(), ex=CACHE_EXPIRE_IN_SECONDS)

    async def get_list(self, key: str, model: Type[T]) -> Optional[dict[str, Any]]:
        data = await self.redis.get(key)
        if not data:
            return None
        parsed = json.loads(data)
        return {
            'items': [model(**item) for item in parsed['items']],
            'total': parsed['total'],
        }

    async def set_list(self, key: str, result: dict[str, Any]) -> None:
        if result['total'] == 0:
            return
        payload = {
            'items': [item.dict(by_alias=True) for item in result['items']],
            'total': result['total'],
        }
        await self.redis.set(key, json.dumps(payload), ex=CACHE_EXPIRE_IN_SECONDS)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def delete_by_pattern(self, pattern: str) -> None:
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)

    async def invalidate_lists(self, index: str) -> None:
        for pattern in LIST_CACHE_PATTERNS.get(index, []):
            await self.delete_by_pattern(pattern)

    async def get_valid_model(
        self, elastic: AsyncElasticsearch, index: str, entity_id: str, model: Type[T],
    ) -> Optional[T]:
        cached = await self.get_model(entity_id, model)
        if cached is None:
            return None
        if await elastic.exists(index=index, id=entity_id):
            return cached
        await self.delete(entity_id)
        await self.invalidate_lists(index)
        return None

    async def get_valid_list(
        self,
        elastic: AsyncElasticsearch,
        index: str,
        cache_key: str,
        model: Type[T],
    ) -> Optional[dict[str, Any]]:
        cached = await self.get_list(cache_key, model)
        if cached is None:
            return None

        for item in cached['items']:
            if not await elastic.exists(index=index, id=item.id):
                await self.invalidate_lists(index)
                return None

        return cached
