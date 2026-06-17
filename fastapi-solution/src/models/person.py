from pydantic import BaseModel, Field


class PersonShort(BaseModel):
    id: str = Field(alias='uuid')
    name: str

    class Config:
        populate_by_name = True


class Person(BaseModel):
    id: str = Field(alias='uuid')  # UUID из ES приходит строкой
    full_name: str

    class Config:
        populate_by_name = True
