import logging

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

logger = logging.getLogger(__name__)


def _log_bulk_errors(errors: list) -> None:
    for item in errors[:5]:
        action = item.get('index') or item.get('create') or item.get('update') or {}
        logger.error(
            'bulk failed: id=%s status=%s error=%s',
            action.get('_id'),
            action.get('status'),
            action.get('error'),
        )
    if len(errors) > 5:
        logger.error('bulk failed: %s more errors', len(errors) - 5)


class ElasticsearchLoader:
    def __init__(self, elastic: AsyncElasticsearch, index_name: str) -> None:
        self.elastic = elastic
        self.index_name = index_name

    async def load(self, docs: list[dict], id_field: str = 'uuid') -> None:
        if not docs:
            return
        actions = [
            {'_index': self.index_name, '_id': doc[id_field], '_source': doc}
            for doc in docs
        ]
        ok, err = await async_bulk(self.elastic, actions, raise_on_error=False)
        if err:
            _log_bulk_errors(err)
            raise RuntimeError(f'bulk: {len(err)} errors')
        logger.info('indexed %s', ok)
