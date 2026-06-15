from pydantic import BaseModel


class PersonShort(BaseModel):
    id: str
    name: str


class Person(BaseModel):
    id: str  # UUID из ES приходит строкой
    full_name: str
