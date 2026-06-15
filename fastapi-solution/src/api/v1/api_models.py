from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class GenreShort(BaseModel):
    uuid: UUID
    name: str


class PersonShort(BaseModel):
    uuid: UUID
    full_name: str


class FilmShort(BaseModel):
    uuid: UUID
    title: str
    imdb_rating: Optional[float] = None


class FilmDetail(FilmShort):
    description: Optional[str] = None
    genre: List[GenreShort] = []
    actors: List[PersonShort] = []
    writers: List[PersonShort] = []
    directors: List[PersonShort] = []


class FilmListResponse(BaseModel):
    items: List[FilmShort]
    total: int
    page_number: int
    page_size: int
