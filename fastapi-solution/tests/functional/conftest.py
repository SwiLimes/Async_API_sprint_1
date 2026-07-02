import asyncio
import aiohttp
import pytest_asyncio
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from functional.settings import test_settings


@pytest_asyncio.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(name='es_client', scope='session')
async def es_client():
    es_client = AsyncElasticsearch(
        hosts=[f'http://{test_settings.es_host}:{test_settings.es_port}'],
        verify_certs=False
    )
    yield es_client
    await es_client.close()


@pytest_asyncio.fixture(name='es_write_data')
def es_write_data(es_client):
    async def inner(
            data: list[dict],
            index: str | None = None,
            mapping: dict | None = None,
    ):
        index = index or test_settings.es_index
        mapping = mapping or test_settings.es_index_mapping

        if await es_client.indices.exists(index=index):
            await es_client.indices.delete(index=index)
        await es_client.indices.create(index=index, **mapping)

        updated, errors = await async_bulk(client=es_client, actions=data, refresh=True)

        if errors:
            raise Exception('Ошибка записи данных в Elasticsearch')

    return inner


@pytest_asyncio.fixture(name='es_write_genres')
def es_write_genres(es_write_data, redis_client):
    async def inner(es_data: list[dict]):
        bulk_query: list[dict] = []
        for row in es_data:
            data = {'_index': test_settings.genres_index, '_id': row['id']}
            data.update({'_source': row})
            bulk_query.append(data)

        await redis_client.flushall()
        await es_write_data(
            bulk_query,
            index=test_settings.genres_index,
            mapping=test_settings.genres_index_mapping,
        )

    return inner


@pytest_asyncio.fixture(name='aiohttp_session', scope='session')
async def aiohttp_session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest_asyncio.fixture(name='make_get_request')
def make_get_request(aiohttp_session):
    async def inner(endpoint: str, params: dict = None):
        url = test_settings.service_url + endpoint
        async with aiohttp_session.get(url, params=params) as response:
            try:
                body = await response.json()
            except aiohttp.ContentTypeError:
                body = None
            return {
                'body': body,
                'headers': response.headers,
                'status': response.status
            }

    return inner


@pytest_asyncio.fixture(name='redis_client', scope='session')
async def redis_client():
    client = redis.Redis(
        host=test_settings.redis_host,
        port=test_settings.redis_port,
        decode_responses=True
    )
    yield client
    await client.close()
