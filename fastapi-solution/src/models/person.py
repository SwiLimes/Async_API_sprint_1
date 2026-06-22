from pydantic import BaseModel, Field


class PersonShort(BaseModel):
    id: str = Field(alias='uuid')
    full_name: str = Field(alias='name')

    class Config:
        populate_by_name = True


class Person(BaseModel):
    id: str = Field(alias='uuid')  # UUID из ES приходит строкой
    full_name: str
    roles: list[str] = Field(default_factory=list)
    film_ids: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True
