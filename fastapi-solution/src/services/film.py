from functools import lru_cache
from typing import Optional, Any, Dict

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


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
        self.redis = redis
        self.elastic = elastic

    # get_by_id возвращает объект фильма. Он опционален, так как фильм может отсутствовать в базе
    async def get_by_id(self, film_id: str) -> Optional[Film]:
        # Пытаемся получить данные из кеша, потому что оно работает быстрее
        film = await self._film_from_cache(film_id)
        if not film:
            # Если фильма нет в кеше, то ищем его в Elasticsearch
            film = await self._get_film_from_elastic(film_id)
            if not film:
                # Если он отсутствует в Elasticsearch, значит, фильма вообще нет в базе
                return None
            # Сохраняем фильм в кеш
            await self._put_film_to_cache(film)

        return film

    async def get_list(
            self,
            sort: Optional[str] = None,
            genre_uuid: Optional[str] = None,
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Получить список фильмов с фильтрацией по жанру и сортировкой.
        Возвращает {'items': List[Film], 'total': int}
        """
        body = _build_search_query(query=None, genre_uuid=genre_uuid, sort=sort, page_size=page_size,
                                        offset=offset)
        return await self._execute_search(body)

    async def search(
            self,
            query: str,
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Поиск фильмов по тексту (название, описание)
        Возвращает {'items': List[Film], 'total': int}
        """
        body = _build_search_query(query=query, genre_uuid=None, sort='-imdb_rating',
                                        page_size=page_size, offset=offset)
        return await self._execute_search(body)

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        try:
            doc = await self.elastic.get(index='movies', id=film_id)
        except NotFoundError:
            return None
        return Film(**doc['_source'])

    async def _film_from_cache(self, film_id: str) -> Optional[Film]:
        # Пытаемся получить данные о фильме из кеша, используя команду get
        # https://redis.io/commands/get/
        data = await self.redis.get(film_id)
        if not data:
            return None

        # pydantic предоставляет удобное API для создания объекта моделей из json
        film = Film.parse_raw(data)
        return film

    async def _put_film_to_cache(self, film: Film):
        # Сохраняем данные о фильме, используя команду set
        # Выставляем время жизни кеша — 5 минут
        # https://redis.io/commands/set/
        # pydantic позволяет сериализовать модель в json
        await self.redis.set(film.id, film.json(), FILM_CACHE_EXPIRE_IN_SECONDS)

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
