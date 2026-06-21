from functools import lru_cache
from typing import Any, Dict, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends

from db.elastic import get_elastic
from models.person import Person


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
    def __init__(self, elastic: AsyncElasticsearch):
        self.elastic = elastic

    async def get_by_id(self, person_id: str) -> Optional[Person]:
        try:
            doc = await self.elastic.get(index='persons', id=person_id)
        except NotFoundError:
            return None
        return self._make_person(doc['_source'], doc['_id'])

    async def get_list(
            self,
            query: Optional[str] = None,
            role: Optional[str] = None,
            sort: Optional[str] = 'full_name',
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
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
        return {'items': items, 'total': total}

    def _make_person(self, source: dict, document_id: str) -> Person:
        data = dict(source)
        data['uuid'] = data.get('uuid') or data.get('id') or document_id
        films = data.get('films') or []

        # Некоторые ETL складывают роли и фильмы внутрь films, а API удобнее отдавать плоско.
        if films and not data.get('film_ids'):
            data['film_ids'] = [
                film_id
                for film in films
                if (film_id := film.get('uuid') or film.get('id'))
            ]
        if films and not data.get('roles'):
            data['roles'] = sorted(
                {
                    role
                    for film in films
                    for role in film.get('roles', [])
                }
            )

        return Person(**data)


@lru_cache()
def get_person_service(
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    return PersonService(elastic)
