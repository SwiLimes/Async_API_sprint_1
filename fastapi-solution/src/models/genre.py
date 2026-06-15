from pydantic import BaseModel


class Genre(BaseModel):
    id: str  # UUID из ES приходит строкой
    name: str
    description: str | None = None
