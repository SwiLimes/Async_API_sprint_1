from functools import lru_cache
from typing import Optional, Any, Dict

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from core.cache import Cache
from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film


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


class FilmService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.elastic = elastic
        self.cache = Cache(redis)
        
    async def get_by_id(self, film_id: str) -> Optional[Film]:
        film = await self.cache.get_valid_model(
            self.elastic, index='movies', entity_id=film_id, model=Film
        )
        if film:
            return film

        film = await self._get_film_from_elastic(film_id)
        if not film:
            return None
        await self.cache.set_model(film_id, film)
        return film

    async def get_list(
            self,
            sort: Optional[str] = None,
            genre_uuid: Optional[str] = None,
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        cache_key = f'films:list:{sort}:{genre_uuid}:{page_size}:{offset}'
        cached = await self.cache.get_valid_list(
            self.elastic, index='movies', cache_key=cache_key, model=Film
        )
        if cached is not None:
            return cached

        body = _build_search_query(
            query=None,
            genre_uuid=genre_uuid,
            sort=sort,
            page_size=page_size,
            offset=offset,
        )
        result = await self._execute_search(body)
        await self.cache.set_list(cache_key, result)
        return result

    async def search(
            self,
            query: str,
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        cache_key = f'films:search:{query}:{page_size}:{offset}'
        cached = await self.cache.get_valid_list(
            self.elastic, index='movies', cache_key=cache_key, model=Film
        )
        if cached is not None:
            return cached

        body = _build_search_query(
            query=query,
            genre_uuid=None,
            sort='-imdb_rating',
            page_size=page_size,
            offset=offset,
        )
        result = await self._execute_search(body)
        await self.cache.set_list(cache_key, result)
        return result

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        try:
            doc = await self.elastic.get(index='movies', id=film_id)
        except NotFoundError:
            return None
        return Film(**doc['_source'])

    async def _execute_search(self, body: dict) -> dict:
        """Выполнить поиск в ES и вернуть {items: List[Film], total: int}"""
        response = await self.elastic.search(index="movies", body=body)
        total = response["hits"]["total"]["value"]
        hits = [hit["_source"] for hit in response["hits"]["hits"]]
        items = [Film(**item) for item in hits]
        return {"items": items, "total": total}


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis, elastic)
