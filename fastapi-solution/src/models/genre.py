from pydantic import BaseModel, Field


class Genre(BaseModel):
    id: str = Field(alias='uuid')  # UUID из ES приходит строкой
    name: str
    description: str | None = None

    class Config:
        populate_by_name = True
