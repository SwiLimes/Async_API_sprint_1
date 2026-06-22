import os
from logging import config as logging_config
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    project_name: str = Field(default='movies', alias='PROJECT_NAME')
    redis_host: str = Field(default='127.0.0.1', alias='REDIS_HOST')
    redis_port: str = Field(default='6379', alias='REDIS_PORT')
    elastic_host: str = Field(default='127.0.0.1', alias='ELASTIC_HOST')
    elastic_port: int = Field(default=9200, alias='ELASTIC_PORT')
    postgres_user: str = Field(default='postgres', alias='POSTGRES_USER')
    postgres_password: str = Field(default='secret', alias='POSTGRES_PASSWORD')
    postgres_db: str = Field(default='theatre', alias='POSTGRES_DB')
    postgres_host: str = Field(default='127.0.0.1', alias='POSTGRES_HOST')
    postgres_port: str = Field(default='5432', alias='POSTGRES_PORT')
    postgres_file_path: str = Field(default='database_dump.sql', alias='POSTGRES_FILE_PATH')
    state_file_path: str = Field(default='/opt/etl/state/state.json', alias='STATE_FILEPATH')


settings = Settings()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
