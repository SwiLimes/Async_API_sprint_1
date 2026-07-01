from functools import lru_cache
from typing import Any, Dict, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.person import Person
from core.cache import Cache


def _build_person_query(
        query: Optional[str],
        role: Optional[str],
        sort: Optional[str],
        page_size: int,
        offset: int,
) -> Dict:
    body = {'from': offset, 'size': page_size}
    must = []
    filters = []

    if query:
        must.append({'multi_match': {'query': query, 'fields': ['full_name^2']}})
    if role:
        filters.append({'term': {'roles': role}})

    if must or filters:
        body['query'] = {'bool': {'must': must or [{'match_all': {}}], 'filter': filters}}
    else:
        body['query'] = {'match_all': {}}

    if sort:
        sort_field = sort[1:] if sort.startswith('-') else sort
        order = 'desc' if sort.startswith('-') else 'asc'
        body['sort'] = [{f'{sort_field}.raw': {'order': order}}]

    return body


class PersonService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.elastic = elastic
        self.cache = Cache(redis)
        
    async def get_by_id(self, person_id: str) -> Optional[Person]:
        person = await self.cache.get_valid_model(
            self.elastic, index='persons', entity_id=person_id, model=Person
        )
        if person:
            return person

        person = await self._get_person_from_elastic(person_id)
        if not person:
            return None
        await self.cache.set_model(person_id, person)
        return person

    async def get_list(
            self,
            query: Optional[str] = None,
            role: Optional[str] = None,
            sort: Optional[str] = 'full_name',
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
        cache_key = f'persons:list:{query}:{role}:{sort}:{page_size}:{offset}'
        cached = await self.cache.get_valid_list(
            self.elastic, index='persons', cache_key=cache_key, model=Person
        )
        if cached is not None:
            return cached

        body = _build_person_query(
            query=query,
            role=role,
            sort=sort,
            page_size=page_size,
            offset=offset,
        )
        response = await self.elastic.search(index='persons', body=body)
        total = response['hits']['total']['value']
        items = [
            self._make_person(hit['_source'], hit['_id'])
            for hit in response['hits']['hits']
        ]
        result = {'items': items, 'total': total}
        await self.cache.set_list(cache_key, result)
        return result

    async def _get_person_from_elastic(self, person_id: str) -> Optional[Person]:
        try:
            doc = await self.elastic.get(index='persons', id=person_id)
        except NotFoundError:
            return None
        return self._make_person(doc['_source'], doc['_id'])

    def _make_person(self, source: dict, document_id: str) -> Person:
        data = dict(source)
        data['uuid'] = data.get('uuid') or data.get('id') or document_id
        if 'roles' not in data:
            data['roles'] = []
        if 'film_ids' not in data:
            data['film_ids'] = []
        return Person(**data)


@lru_cache()
def get_person_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    return PersonService(redis, elastic)
