import uuid

import pytest

from functional.settings import test_settings


@pytest.mark.asyncio
async def test_get_genre_by_id(make_get_request, es_write_genres):
    genre_id = str(uuid.uuid4())

    es_data = [{'id': genre_id, 'name': 'Super Action', 'description': 'Action movies'}]

    await es_write_genres(es_data)

    response = await make_get_request(f'/api/v1/genres/{genre_id}')

    assert response['status'] == 200
    assert response['body']['uuid'] == genre_id
    assert response['body']['name'] == 'Super Action'
    assert response['body']['description'] == 'Action movies'


@pytest.mark.asyncio
async def test_get_genre_not_found(make_get_request, redis_client):
    await redis_client.flushall()

    response = await make_get_request(f'/api/v1/genres/{uuid.uuid4()}')

    assert response['status'] == 404
    assert response['body']['detail'] == 'genre not found'


@pytest.mark.asyncio
async def test_list_all_genres(make_get_request, es_write_genres):
    es_data = [
        {'id': str(uuid.uuid4()), 'name': 'Action', 'description': 'Action movies'}
        for _ in range(5)
    ]

    await es_write_genres(es_data)

    response = await make_get_request('/api/v1/genres')

    assert response['status'] == 200
    assert response['body']['total'] == 5
    assert len(response['body']['items']) == 5


@pytest.mark.asyncio
async def test_list_genres_page_size(make_get_request, es_write_genres):
    es_data = [
        {'id': str(uuid.uuid4()), 'name': 'Action', 'description': 'Action movies'}
        for _ in range(60)
    ]

    await es_write_genres(es_data)

    response = await make_get_request('/api/v1/genres')

    assert response['status'] == 200
    assert response['body']['total'] == 60
    assert len(response['body']['items']) == 50
    assert response['body']['page_size'] == 50
    assert response['body']['page_number'] == 1


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        (
            {'query': 'Action'},
            {'status': 200, 'length': 50, 'total': 60},
        ),
        (
            {'query': 'Mashed potato'},
            {'status': 200, 'length': 0, 'total': 0},
        ),
    ]
)
@pytest.mark.asyncio
async def test_search_genres(make_get_request, es_write_genres, query_data, expected_answer):
    es_data = [
        {'id': str(uuid.uuid4()), 'name': 'Action', 'description': 'Action movies'}
        for _ in range(60)
    ]

    await es_write_genres(es_data)

    response = await make_get_request('/api/v1/genres', params=query_data)

    assert response['status'] == expected_answer['status']
    assert len(response['body']['items']) == expected_answer['length']
    assert response['body']['total'] == expected_answer['total']


@pytest.mark.parametrize(
    'params, expected_status',
    [
        ({'page_number': 0}, 422),
        ({'page_size': 0}, 422),
        ({'page_size': 101}, 422),
        ({'sort': 'title'}, 422),
        ({'query': ''}, 422),
        ({'sort': 'name'}, 200),
    ]
)
@pytest.mark.asyncio
async def test_genre_list_validation(make_get_request, params, expected_status):
    response = await make_get_request('/api/v1/genres', params=params)

    assert response['status'] == expected_status


@pytest.mark.asyncio
async def test_genre_by_id_redis_cache(make_get_request, es_write_genres, redis_client):
    genre_id = str(uuid.uuid4())
    es_data = [{'id': genre_id, 'name': 'Drama', 'description': 'Drama movies'}]

    await es_write_genres(es_data)

    response_first = await make_get_request(f'/api/v1/genres/{genre_id}')
    assert await redis_client.get(genre_id) is not None

    response_second = await make_get_request(f'/api/v1/genres/{genre_id}')

    assert response_first['status'] == 200
    assert response_second['status'] == 200
    assert response_second['body'] == response_first['body']


@pytest.mark.asyncio
async def test_genre_by_id_cache_cleared_after_es_delete(
        make_get_request,
        es_write_genres,
        es_client,
        redis_client,
):
    genre_id = str(uuid.uuid4())
    es_data = [{'id': genre_id, 'name': 'Drama', 'description': 'Drama movies'}]

    await es_write_genres(es_data)
    await make_get_request(f'/api/v1/genres/{genre_id}')

    await es_client.delete(index=test_settings.genres_index, id=genre_id)

    response = await make_get_request(f'/api/v1/genres/{genre_id}')

    assert response['status'] == 404
    assert await redis_client.get(genre_id) is None


@pytest.mark.asyncio
async def test_genre_list_redis_cache(make_get_request, es_write_genres, redis_client):
    es_data = [
        {'id': str(uuid.uuid4()), 'name': 'Action', 'description': 'Action movies'}
        for _ in range(5)
    ]

    await es_write_genres(es_data)

    response_first = await make_get_request('/api/v1/genres')
    cache_key = 'genres:list:None:name:50:0'
    assert await redis_client.get(cache_key) is not None

    response_second = await make_get_request('/api/v1/genres')

    assert response_first['status'] == 200
    assert response_second['status'] == 200
    assert response_second['body'] == response_first['body']


@pytest.mark.asyncio
async def test_genre_list_cache_cleared_after_es_delete(
        make_get_request,
        es_write_genres,
        es_client,
        redis_client,
):
    genre_id = str(uuid.uuid4())
    es_data = [{'id': genre_id, 'name': 'Drama', 'description': 'Drama movies'}]
    es_data.extend(
        {'id': str(uuid.uuid4()), 'name': 'Action', 'description': 'Action movies'}
        for _ in range(4)
    )

    await es_write_genres(es_data)

    response_first = await make_get_request('/api/v1/genres')
    cache_key = 'genres:list:None:name:50:0'
    assert response_first['status'] == 200
    assert response_first['body']['total'] == 5
    assert await redis_client.get(cache_key) is not None

    await es_client.delete(index=test_settings.genres_index, id=genre_id, refresh=True)

    response_second = await make_get_request('/api/v1/genres')

    assert response_second['status'] == 200
    assert response_second['body']['total'] == 4
    genre_uuids = [genre['uuid'] for genre in response_second['body']['items']]
    assert genre_id not in genre_uuids


@pytest.mark.asyncio
async def test_genre_by_id_clears_list_cache_after_es_delete(
        make_get_request,
        es_write_genres,
        es_client,
        redis_client,
):
    genre_id = str(uuid.uuid4())
    es_data = [{'id': genre_id, 'name': 'Drama', 'description': 'Drama movies'}]

    await es_write_genres(es_data)
    await make_get_request('/api/v1/genres')
    await make_get_request(f'/api/v1/genres/{genre_id}')

    cache_key = 'genres:list:None:name:50:0'
    assert await redis_client.get(cache_key) is not None
    assert await redis_client.get(genre_id) is not None

    await es_client.delete(index=test_settings.genres_index, id=genre_id, refresh=True)

    response = await make_get_request(f'/api/v1/genres/{genre_id}')

    assert response['status'] == 404
    assert await redis_client.get(genre_id) is None
    assert await redis_client.get(cache_key) is None
