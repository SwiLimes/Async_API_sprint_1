# Используем pydantic для упрощения работы при перегонке данных из json в объекты
from pydantic import BaseModel

from models.person import PersonShort

# Это потом добавим в индекс ES, пока не нужно
# class FilmShort(BaseModel):
#     id: str
#     title: str


class Film(BaseModel):
    id: str  # UUID из ES приходит строкой
    title: str
    description: str
    imdb_rating: float | None = None
    genres: list[str] = []
    actors: list[PersonShort] = []
    directors: list[PersonShort] = []
    writers: list[PersonShort] = []
    actors_names: list[str] = []
    directors_names: list[str] = []
    writers_names: list[str] = []
