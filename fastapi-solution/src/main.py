from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis

from api.v1 import films, genres, persons
import asyncio
from core import config
from db import elastic, redis
from etl.etl_operations import etl_process

app = FastAPI(
    title=config.PROJECT_NAME,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse,
)


@app.on_event('startup')
async def startup():
    redis.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)
    elastic.es = AsyncElasticsearch(
        hosts=[f'http://{config.ELASTIC_HOST}:{config.ELASTIC_PORT}']
    )
    asyncio.create_task(etl_process(elastic.es))


@app.on_event('shutdown')
async def shutdown():
    await redis.redis.close()
    await elastic.es.close()


# Подключаем роутеры к серверу, теги нужны для удобной навигации в документации.
app.include_router(films.router, prefix='/api/v1/films', tags=['films'])
app.include_router(genres.router, prefix='/api/v1/genres', tags=['genres'])
app.include_router(persons.router, prefix='/api/v1/persons', tags=['persons'])
