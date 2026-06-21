import json
from functools import lru_cache
from typing import Any, Dict, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.person import Person

PERSON_CACHE_EXPIRE_IN_SECONDS = 60 * 5


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
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, person_id: str) -> Optional[Person]:
        person = await self._person_from_cache(person_id)
        if not person:
            person = await self._get_person_from_elastic(person_id)
            if not person:
                return None
            await self._put_person_to_cache(person_id, person)
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
        cached = await self._list_from_cache(cache_key)
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
        await self._put_list_to_cache(cache_key, result)
        return result

    async def _get_person_from_elastic(self, person_id: str) -> Optional[Person]:
        try:
            doc = await self.elastic.get(index='persons', id=person_id)
        except NotFoundError:
            return None
        return self._make_person(doc['_source'], doc['_id'])

    async def _person_from_cache(self, person_id: str) -> Optional[Person]:
        data = await self.redis.get(person_id)
        if not data:
            return None
        return Person.parse_raw(data)

    async def _put_person_to_cache(self, person_id: str, person: Person) -> None:
        await self.redis.set(person_id, person.json(), ex=PERSON_CACHE_EXPIRE_IN_SECONDS)

    async def _list_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        data = await self.redis.get(cache_key)
        if not data:
            return None
        parsed = json.loads(data)
        return {
            'items': [Person(**item) for item in parsed['items']],
            'total': parsed['total'],
        }

    async def _put_list_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        if result['total'] == 0:
            return
        payload = {
            'items': [person.dict(by_alias=True) for person in result['items']],
            'total': result['total'],
        }
        await self.redis.set(cache_key, json.dumps(payload), ex=PERSON_CACHE_EXPIRE_IN_SECONDS)

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
