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
async def es_write_data(es_client):
    async def inner(data: list[dict]):
        if await es_client.indices.exists(index=test_settings.es_index):
            await es_client.indices.delete(index=test_settings.es_index)
        await es_client.indices.create(index=test_settings.es_index, **test_settings.es_index_mapping)

        updated, errors = await async_bulk(client=es_client, actions=data, refresh=True)

        if errors:
            raise Exception('Ошибка записи данных в Elasticsearch')

    return inner


@pytest_asyncio.fixture(name='make_get_request')
async def make_get_request():
    async def inner(endpoint: str, params: dict = None):
        async with aiohttp.ClientSession() as session:
            url = test_settings.service_url + endpoint
            async with session.get(url, params=params) as response:
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
