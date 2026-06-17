from http import HTTPStatus
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.v1.api_models import FilmDetail, FilmShort, FilmListResponse, GenreShort, PersonShort
from core.dependencies import PaginationParams
from models.film import Film
from services.film import FilmService, get_film_service

router = APIRouter()


def _to_film_short(film: Film) -> FilmShort:
    return FilmShort(
        uuid=UUID(film.id),
        title=film.title,
        imdb_rating=film.imdb_rating,
    )


def _to_film_detail(film: Film) -> FilmDetail:
    return FilmDetail(
        uuid=UUID(film.id),
        title=film.title,
        imdb_rating=film.imdb_rating,
        description=film.description,
        genre=[GenreShort(uuid=UUID(g.id), name=g.name) for g in film.genres],
        actors=[PersonShort(uuid=UUID(a.id), full_name=a.full_name) for a in film.actors],
        writers=[PersonShort(uuid=UUID(w.id), full_name=w.full_name) for w in film.writers],
        directors=[PersonShort(uuid=UUID(d.id), full_name=d.full_name) for d in film.directors],
    )


@router.get(
    '/',
    response_model=FilmListResponse,
    summary='Список фильмов',
    description="""Возвращает список фильмов с поддержкой пагинации, сортировки по рейтингу IMDb 
            и фильтрации по жанру. Используется для главной страницы (популярные фильмы)
            и для показа фильмов конкретного жанра""",
    response_description="Список фильмов и информация о пагинации"
)
async def get_films(
        sort: Optional[str] = Query(
            None,
            regex='^-?imdb_rating$',
            description="""Сортировка по рейтингу IMDB.
            `-imdb_rating` от высокого к низкому (популярные сначала),
            `imdb_rating` от низкого к высокому. По умолчанию не используется""",
            example='-imdb_rating',
        ),
        genre: Optional[UUID] = Query(
            None,
            description="UUID жанра для фильтрации",
            example='6f822a92-7b51-4753-8d00-ecfedf98a937'
        ),
        pagination: PaginationParams = Depends(),
        film_service: FilmService = Depends(get_film_service),
) -> FilmListResponse:
    """
    Получение списка фильмов.

    :param sort: Опциональный параметр сортировки по `imdb_rating`.
    :param genre: UUID жанра для фильтрации.
    :param pagination: Параметры пагинации page_number и page_size
    :param film_service: Сервис для работы с фильмами
    """
    result = await film_service.get_list(
        sort=sort,
        genre_uuid=str(genre) if genre else None,
        page_size=pagination.page_size,
        offset=pagination.offset)
    films = [_to_film_short(film) for film in result['items']]
    return FilmListResponse(
        items=films,
        total=result['total'],
        page_number=pagination.page_number,
        page_size=pagination.page_size,
    )


@router.get(
    '/search',
    response_model=FilmListResponse,
    summary='Поиск фильмов',
    description='Полнотекстовый поиск по названию и описанию фильма. Возвращает список фильмов с пагинацией',
    response_description='Список найденных фильмов и информации о пагинации',
)
async def search_films(
        query: str = Query(
            ...,
            min_length=1,
            description='Поисковой запрос',
            example='star'),
        pagination: PaginationParams = Depends(),
        film_service: FilmService = Depends(get_film_service),
) -> FilmListResponse:
    """
    Поиск фильмов по текстовому запросу.

    :param query: Обязательный поисковый запрос (минимум 1 символ).
    :param pagination: Параметры пагинации page_number и page_size
    :param film_service: Сервис для работы с фильмами

    Результаты сортируются по рейтингу IMDb от высокого к низкому.
    """
    result = await film_service.search(
        query=query,
        page_size=pagination.page_size,
        offset=pagination.offset,
    )
    films = [_to_film_short(film) for film in result['items']]
    return FilmListResponse(
        items=films,
        total=result['total'],
        page_number=pagination.page_number,
        page_size=pagination.page_size,
    )


# Внедряем FilmService с помощью Depends(get_film_service)
@router.get(
    '/{film_id}',
    response_model=FilmDetail,
    summary='Детальная информация о фильме',
    description='Возвращает полную информацию о фильме: описание, список жанров, актёров, сценаристов, режиссёров.',
    response_description='Полный объект фильма со всеми полями'
)
async def film_details(
        film_id: str,
        film_service: FilmService = Depends(get_film_service)
) -> FilmDetail:
    """
    Получение фильма по его UUID.

    :param film_id: UUID фильма
    :param film_service: Сервис для работы с фильмами

    Если фильм не найден, возвращается ошибка 404.
    """
    film = await film_service.get_by_id(film_id)
    if not film:
        # Если фильм не найден, отдаём 404 статус
        # Желательно пользоваться уже определёнными HTTP-статусами, которые содержат enum    # Такой код будет более поддерживаемым
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')
    return _to_film_detail(film)
