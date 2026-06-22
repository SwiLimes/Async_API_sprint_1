import json
from functools import lru_cache
from typing import Any, Dict, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.genre import Genre

GENRE_CACHE_EXPIRE_IN_SECONDS = 60 * 5


def _build_genre_query(
        query: Optional[str],
        sort: Optional[str],
        page_size: int,
        offset: int,
) -> Dict:
    body = {'from': offset, 'size': page_size}
    body['query'] = (
        {'multi_match': {'query': query, 'fields': ['name^2', 'description']}}
        if query
        else {'match_all': {}}
    )

    if sort:
        sort_field = sort[1:] if sort.startswith('-') else sort
        order = 'desc' if sort.startswith('-') else 'asc'
        body['sort'] = [{sort_field: {'order': order}}]

    return body


class GenreService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, genre_id: str) -> Optional[Genre]:
        genre = await self._genre_from_cache(genre_id)
        if not genre:
            genre = await self._get_genre_from_elastic(genre_id)
            if not genre:
                return None
            await self._put_genre_to_cache(genre_id, genre)
        return genre

    async def get_list(
            self,
            query: Optional[str] = None,
            sort: Optional[str] = 'name',
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        cache_key = f'genres:list:{query}:{sort}:{page_size}:{offset}'
        cached = await self._list_from_cache(cache_key)
        if cached is not None:
            return cached

        body = _build_genre_query(
            query=query,
            sort=sort,
            page_size=page_size,
            offset=offset,
        )
        response = await self.elastic.search(index='genres', body=body)
        total = response['hits']['total']['value']
        items = [
            self._make_genre(hit['_source'], hit['_id'])
            for hit in response['hits']['hits']
        ]
        result = {'items': items, 'total': total}
        await self._put_list_to_cache(cache_key, result)
        return result

    async def _get_genre_from_elastic(self, genre_id: str) -> Optional[Genre]:
        try:
            doc = await self.elastic.get(index='genres', id=genre_id)
        except NotFoundError:
            return None
        return self._make_genre(doc['_source'], doc['_id'])

    async def _genre_from_cache(self, genre_id: str) -> Optional[Genre]:
        data = await self.redis.get(genre_id)
        if not data:
            return None
        return Genre.parse_raw(data)

    async def _put_genre_to_cache(self, genre_id: str, genre: Genre) -> None:
        await self.redis.set(genre_id, genre.json(), ex=GENRE_CACHE_EXPIRE_IN_SECONDS)

    async def _list_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        data = await self.redis.get(cache_key)
        if not data:
            return None
        parsed = json.loads(data)
        return {
            'items': [Genre(**item) for item in parsed['items']],
            'total': parsed['total'],
        }

    async def _put_list_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        if result['total'] == 0:
            return
        payload = {
            'items': [genre.dict(by_alias=True) for genre in result['items']],
            'total': result['total'],
        }
        await self.redis.set(cache_key, json.dumps(payload), ex=GENRE_CACHE_EXPIRE_IN_SECONDS)

    def _make_genre(self, source: dict, document_id: str) -> Genre:
        data = dict(source)
        data['uuid'] = data.get('uuid') or data.get('id') or document_id
        return Genre(**data)


@lru_cache()
def get_genre_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(redis, elastic)
