from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.v1.api_models import GenreDetail, GenreListResponse
from core.dependencies import PaginationParams
from models.genre import Genre
from services.genre import GenreService, get_genre_service

router = APIRouter()


def _to_genre_detail(genre: Genre) -> GenreDetail:
    return GenreDetail(
        uuid=UUID(genre.id),
        name=genre.name,
        description=genre.description,
    )


@router.get(
    '/',
    response_model=GenreListResponse,
    summary='Список жанров',
    description='Возвращает список жанров с пагинацией, поиском по тексту и сортировкой по названию.',
    response_description='Список жанров и информация о пагинации',
)
async def get_genres(
        sort: str = Query(
            'name',
            regex='^-?name$',
            description='Сортировка по названию жанра: name или -name.',
            example='name',
        ),
        query: str | None = Query(
            None,
            min_length=1,
            description='Поиск по названию и описанию жанра',
            example='action',
        ),
        pagination: PaginationParams = Depends(),
        genre_service: GenreService = Depends(get_genre_service),
) -> GenreListResponse:
    result = await genre_service.get_list(
        query=query,
        sort=sort,
        page_size=pagination.page_size,
        offset=pagination.offset,
    )
    return GenreListResponse(
        items=[_to_genre_detail(genre) for genre in result['items']],
        total=result['total'],
        page_number=pagination.page_number,
        page_size=pagination.page_size,
    )


@router.get(
    '/{genre_id}',
    response_model=GenreDetail,
    summary='Детальная информация о жанре',
    description='Возвращает жанр по UUID.',
    response_description='Информация о жанре',
)
async def genre_details(
        genre_id: str,
        genre_service: GenreService = Depends(get_genre_service),
) -> GenreDetail:
    genre = await genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='genre not found')
    return _to_genre_detail(genre)
