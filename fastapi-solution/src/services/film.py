from functools import lru_cache
from typing import Optional, Any, Dict, List

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film
from services.cache import RedisCache

FILM_DETAIL_PREFIX = 'film:detail'
FILM_LIST_PREFIX = 'film:list'
FILM_SEARCH_PREFIX = 'film:search'


def _build_search_query(
        query: Optional[str],
        genre_uuid: Optional[str],
        sort: Optional[str],
        page_size: int,
        offset: int,
) -> Dict:
    body = {'from': offset, 'size': page_size}
    must = []
    if query:
        must.append({'multi_match': {'query': query, 'fields': ['title^3', 'description']}})
    if genre_uuid:
        must.append({
            'nested': {
                'path': 'genre',
                'query': {'term': {'genre.uuid': genre_uuid}}
            }
        })
    body['query'] = {'bool': {'must': must}} if must else {'match_all': {}}
    if sort:
        sort_field = sort[1:] if sort.startswith('-') else sort
        order = 'desc' if sort.startswith('-') else 'asc'
        body['sort'] = [{sort_field: {'order': order}}]
    else:
        body['sort'] = [{'imdb_rating': {'order': 'desc'}}]
    return body


def _serialize_search_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'items': [film.model_dump(by_alias=True) for film in result['items']],
        'total': result['total'],
    }


def _deserialize_search_result(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'items': [Film(**item) for item in data['items']],
        'total': data['total'],
    }


class FilmService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic
        self._detail_cache = RedisCache(redis, FILM_DETAIL_PREFIX)
        self._list_cache = RedisCache(redis, FILM_LIST_PREFIX)
        self._search_cache = RedisCache(redis, FILM_SEARCH_PREFIX)

    async def get_by_id(self, film_id: str) -> Optional[Film]:
        cache_key = self._detail_cache.key(film_id=film_id)
        film = await self._get_film_from_cache(cache_key)
        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(cache_key, film)

        return film

    async def get_list(
            self,
            sort: Optional[str] = None,
            genre_uuid: Optional[str] = None,
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        cache_key = self._list_cache.key(
            sort=sort,
            genre=genre_uuid,
            page_size=page_size,
            offset=offset,
        )
        cached = await self._list_cache.get_json(cache_key)
        if cached is not None:
            return _deserialize_search_result(cached)

        body = _build_search_query(
            query=None,
            genre_uuid=genre_uuid,
            sort=sort,
            page_size=page_size,
            offset=offset,
        )
        result = await self._execute_search(body)
        await self._list_cache.set_json(cache_key, _serialize_search_result(result))
        return result

    async def search(
            self,
            query: str,
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        cache_key = self._search_cache.key(
            query=query,
            page_size=page_size,
            offset=offset,
        )
        cached = await self._search_cache.get_json(cache_key)
        if cached is not None:
            return _deserialize_search_result(cached)

        body = _build_search_query(
            query=query,
            genre_uuid=None,
            sort='-imdb_rating',
            page_size=page_size,
            offset=offset,
        )
        result = await self._execute_search(body)
        await self._search_cache.set_json(cache_key, _serialize_search_result(result))
        return result

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        try:
            doc = await self.elastic.get(index='movies', id=film_id)
        except NotFoundError:
            return None
        return Film(**doc['_source'])

    async def _get_film_from_cache(self, cache_key: str) -> Optional[Film]:
        data = await self._detail_cache.get_json(cache_key)
        if not data:
            return None
        return Film(**data)

    async def _put_film_to_cache(self, cache_key: str, film: Film) -> None:
        await self._detail_cache.set_json(cache_key, film.model_dump(by_alias=True))

    async def _execute_search(self, body: dict) -> dict:
        response = await self.elastic.search(index='movies', body=body)
        total = response['hits']['total']['value']
        hits: List[dict] = [hit['_source'] for hit in response['hits']['hits']]
        items = [Film(**item) for item in hits]
        return {'items': items, 'total': total}


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis, elastic)
