import os
from logging import config as logging_config

from core.logger import LOGGING

logging_config.dictConfig(LOGGING)

PROJECT_NAME = os.getenv('PROJECT_NAME', 'movies')

REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

ELASTIC_HOST = os.getenv('ELASTIC_HOST', '127.0.0.1')
ELASTIC_PORT = int(os.getenv('ELASTIC_PORT', '9200'))

POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'secret')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'theatre')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', '127.0.0.1')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_FILE_PATH = os.getenv('POSTGRES_FILE_PATH', 'database_dump.sql')
STATE_FILEPATH = os.getenv('STATE_FILEPATH', '/opt/etl/state/state.json')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CACHE_EXPIRE_IN_SECONDS = int(os.getenv('CACHE_EXPIRE_IN_SECONDS', 300))
