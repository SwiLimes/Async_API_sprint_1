from pydantic import Field
from pydantic_settings import BaseSettings

from functional.testdata.es_mapping import MAPPING_MOVIES


class TestSettings(BaseSettings):
    es_host: str = Field(default='127.0.0.1', alias='ELASTIC_HOST')
    es_port: int = Field(default=9200, alias='ELASTIC_PORT')
    es_index: str = Field(default='movies', alias='ES_INDEX')
    es_id_field: str = Field(default='id', alias='ES_ID_FIELD')
    es_index_mapping: dict = Field(default=MAPPING_MOVIES)
    redis_host: str = Field(default='127.0.0.1', alias='REDIS_HOST')
    redis_port: int = Field(default=6379, alias='REDIS_PORT')
    service_url: str = Field(default='http://127.0.0.1:8000', alias='SERVICE_URL')


test_settings = TestSettings()
