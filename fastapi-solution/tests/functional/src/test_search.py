import datetime
import uuid

import pytest


def make_movie_doc(title: str, description: str = 'Some description', rating: float = 8.0) -> dict:
    film_id = str(uuid.uuid4())
    return {
        "_index": "movies",
        "_id": film_id,
        "_source": {
            'id': film_id,
            'imdb_rating': rating,
            'genre': [
                {'id': str(uuid.uuid4()), 'name': 'Action'},
            ],
            'title': title,
            'description': description,
            'actors': [],
            'writers': [],
            'directors': [],
            'actors_names': [],
            'writers_names': [],
            'directors_names': [],
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat(),
            'film_work_type': 'movie',
        },
    }


def make_movies_bulk(count: int, title_prefix: str) -> list[dict]:
    return [
        make_movie_doc(
            title=f"{title_prefix} {index}",
            rating=10 - index / 10,
        )
        for index in range(count)
    ]


@pytest.mark.parametrize(
    'params',
    [
        {},
        {'query': ''},
        {'query': 'star', 'page_number': 0},
        {'query': 'star', 'page_number': -1},
        {'query': 'star', 'page_number': 'abc'},
        {'query': 'star', 'page_size': 0},
        {'query': 'star', 'page_size': -1},
        {'query': 'star', 'page_size': 101},
        {'query': 'star', 'page_size': 'abc'},
    ],
)


@pytest.mark.asyncio
async def test_search_validation_errors(make_get_request, params):
    response = await make_get_request('/api/v1/films/search', params=params)
    assert response['status'] == 422


@pytest.mark.parametrize(
    'params',
    [
        {'query': 'S'},
        {'query': 'star', 'page_number': 1},
        {'query': 'star', 'page_size': 1},
        {'query': 'star', 'page_size': 100},
    ],
)

@pytest.mark.asyncio
async def test_search_validation_valid_boundaries(make_get_request, es_write_data, params):
    await es_write_data([
        make_movie_doc(title='Star Movie'),
    ])

    response = await make_get_request('/api/v1/films/search', params=params)
    assert response['status'] == 200


@pytest.mark.asyncio
async def test_search_returns_only_requested_number_of_records(make_get_request, es_write_data):
    await es_write_data(make_movies_bulk(count=10, title_prefix='Star Movie'))

    response = await make_get_request(
        '/api/v1/films/search',
        params={'query': 'Star', 'page_size': 3},
    )

    assert response['status'] == 200
    assert response['body']['total'] == 10
    assert len(response['body']['items']) == 3
    assert response['body']['page_number'] == 1
    assert response['body']['page_size'] == 3


@pytest.mark.asyncio
async def test_search_uses_page_number_and_page_size(make_get_request, es_write_data):
    await es_write_data([
        make_movie_doc(title='Star Movie 1', rating=9.9),
        make_movie_doc(title='Star Movie 2', rating=9.8),
        make_movie_doc(title='Star Movie 3', rating=9.7),
        make_movie_doc(title='Star Movie 4', rating=9.6),
        make_movie_doc(title='Star Movie 5', rating=9.5),
    ])

    response = await make_get_request(
        '/api/v1/films/search',
        params={'query': 'Star', 'page_number': 2, 'page_size': 2},
    )

    assert response['status'] == 200
    assert response['body']['total'] == 5
    assert response['body']['page_number'] == 2
    assert response['body']['page_size'] == 2
    assert len(response['body']['items']) == 2
    assert response['body']['items'][0]['title'] == 'Star Movie 3'
    assert response['body']['items'][1]['title'] == 'Star Movie 4'


@pytest.mark.asyncio
async def test_search_finds_movie_by_phrase_in_title(make_get_request, es_write_data):
    await es_write_data([
        make_movie_doc(title='The Silver Comet', description='Space story'),
        make_movie_doc(title='Another Movie', description='No matching words here'),
    ])

    response = await make_get_request(
        '/api/v1/films/search',
        params={'query': 'Silver Comet'},
    )

    assert response['status'] == 200
    assert response['body']['total'] == 1
    assert len(response['body']['items']) == 1
    assert response['body']['items'][0]['title'] == 'The Silver Comet'


@pytest.mark.asyncio
async def test_search_finds_movie_by_phrase_in_description(make_get_request, es_write_data):
    await es_write_data([
        make_movie_doc(title='Unknown Title', description='A movie about distant galaxy travel'),
        make_movie_doc(title='Another Movie', description='No matching words here'),
    ])

    response = await make_get_request(
        '/api/v1/films/search',
        params={'query': 'distant galaxy'},
    )

    assert response['status'] == 200
    assert response['body']['total'] == 1
    assert response['body']['items'][0]['title'] == 'Unknown Title'


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_nothing_found(make_get_request, es_write_data):
    await es_write_data([
        make_movie_doc(title='Star Movie'),
    ])

    response = await make_get_request(
        '/api/v1/films/search',
        params={'query': 'Mashed Potato'},
    )

    assert response['status'] == 200
    assert response['body']['total'] == 0
    assert response['body']['items'] == []


@pytest.mark.asyncio
async def test_search_uses_redis_cache(make_get_request, es_write_data, redis_client):
    params = {'query': 'Cached Star', 'page_size': 2}
    cache_key = 'films:search:Cached Star:2:0'

    await es_write_data([
        make_movie_doc(title='Cached Star One', rating=9.0),
        make_movie_doc(title='Cached Star Two', rating=8.0),
    ])

    first_response = await make_get_request('/api/v1/films/search', params=params)

    assert first_response['status'] == 200
    assert first_response['body']['total'] == 2
    assert await redis_client.get(cache_key) is not None

    await es_write_data([
        make_movie_doc(title='Cached Star Changed', rating=10.0),
    ])

    second_response = await make_get_request('/api/v1/films/search', params=params)

    assert second_response['status'] == 200
    assert second_response['body'] == first_response['body']