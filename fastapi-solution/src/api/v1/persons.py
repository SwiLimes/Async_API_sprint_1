from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.v1.api_models import PersonDetail, PersonListResponse
from core.dependencies import PaginationParams
from models.person import Person
from services.person import PersonService, get_person_service

router = APIRouter()


def _to_person_detail(person: Person) -> PersonDetail:
    return PersonDetail(
        uuid=UUID(person.id),
        full_name=person.full_name,
        roles=person.roles,
        film_ids=[UUID(film_id) for film_id in person.film_ids],
    )


@router.get(
    '/',
    response_model=PersonListResponse,
    summary='Список персоналий',
    description='Возвращает список персоналий с пагинацией, поиском, фильтром по роли и сортировкой по имени.',
    response_description='Список персоналий и информация о пагинации',
)
async def get_persons(
        sort: str = Query(
            'full_name',
            regex='^-?full_name$',
            description='Сортировка по имени: full_name или -full_name.',
            example='full_name',
        ),
        query: str | None = Query(
            None,
            min_length=1,
            description='Поиск по имени персоны',
            example='spielberg',
        ),
        role: str | None = Query(
            None,
            min_length=1,
            description='Фильтр по роли в фильмах',
            example='director',
        ),
        pagination: PaginationParams = Depends(),
        person_service: PersonService = Depends(get_person_service),
) -> PersonListResponse:
    result = await person_service.get_list(
        query=query,
        role=role,
        sort=sort,
        page_size=pagination.page_size,
        offset=pagination.offset,
    )
    return PersonListResponse(
        items=[_to_person_detail(person) for person in result['items']],
        total=result['total'],
        page_number=pagination.page_number,
        page_size=pagination.page_size,
    )


@router.get(
    '/search',
    response_model=PersonListResponse,
    summary='Поиск персоналий',
    description='Ищет персоналии по имени и возвращает результат с пагинацией.',
    response_description='Список найденных персоналий и информация о пагинации',
)
async def search_persons(
        query: str = Query(..., min_length=1, description='Поисковой запрос', example='tom'),
        pagination: PaginationParams = Depends(),
        person_service: PersonService = Depends(get_person_service),
) -> PersonListResponse:
    result = await person_service.get_list(
        query=query,
        sort='full_name',
        page_size=pagination.page_size,
        offset=pagination.offset,
    )
    return PersonListResponse(
        items=[_to_person_detail(person) for person in result['items']],
        total=result['total'],
        page_number=pagination.page_number,
        page_size=pagination.page_size,
    )


@router.get(
    '/{person_id}',
    response_model=PersonDetail,
    summary='Детальная информация о персоне',
    description='Возвращает персону по UUID.',
    response_description='Информация о персоне',
)
async def person_details(
        person_id: str,
        person_service: PersonService = Depends(get_person_service),
) -> PersonDetail:
    person = await person_service.get_by_id(person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='person not found')
    return _to_person_detail(person)
