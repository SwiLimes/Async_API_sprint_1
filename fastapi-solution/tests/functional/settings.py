from pydantic import Field
from pydantic_settings import BaseSettings


class TestSettings(BaseSettings):
    es_host: str = Field(default='127.0.0.1', alias='ELASTIC_HOST')
    es_port: int = Field(default=9200, alias='ELASTIC_PORT')
    es_index: str = Field(default='movies', alias='ES_INDEX')
    es_id_field: str = Field(default='id', alias='ES_ID_FIELD')
    es_index_mapping: dict = Field(default={
        "body": {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "imdb_rating": {"type": "float"},
                    "genre": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text"}
                        }
                    },
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "director": {"type": "keyword"},
                    "actors_names": {"type": "keyword"},
                    "writers_names": {"type": "keyword"},
                    "actors": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text"}
                        }
                    },
                    "writers": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text"}
                        }
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "film_work_type": {"type": "keyword"}
                }
            }
        }
    })
    redis_host: str = Field(default='127.0.0.1', alias='REDIS_HOST')
    redis_port: int = Field(default=6379, alias='REDIS_PORT')
    service_url: str = Field(default='http://127.0.0.1:8000', alias='SERVICE_URL')


test_settings = TestSettings()
