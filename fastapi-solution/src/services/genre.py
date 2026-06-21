from functools import lru_cache
from typing import Any, Dict, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends

from db.elastic import get_elastic
from models.genre import Genre


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
        # Для текстовых полей сортируем по keyword-подполю, чтобы ES не считал анализированный текст.
        body['sort'] = [{f'{sort_field}.raw': {'order': order}}]

    return body


class GenreService:
    def __init__(self, elastic: AsyncElasticsearch):
        self.elastic = elastic

    async def get_by_id(self, genre_id: str) -> Optional[Genre]:
        try:
            doc = await self.elastic.get(index='genres', id=genre_id)
        except NotFoundError:
            return None
        return self._make_genre(doc['_source'], doc['_id'])

    async def get_list(
            self,
            query: Optional[str] = None,
            sort: Optional[str] = 'name',
            page_size: int = 50,
            offset: int = 0,
    ) -> Dict[str, Any]:
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
        return {'items': items, 'total': total}

    def _make_genre(self, source: dict, document_id: str) -> Genre:
        data = dict(source)
        data['uuid'] = data.get('uuid') or data.get('id') or document_id
        return Genre(**data)


@lru_cache()
def get_genre_service(
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(elastic)
