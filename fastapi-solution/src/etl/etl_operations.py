import asyncio
import logging

from etl.postgres_db_operator import PostgresDBOperator

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from etl.indices_info import active_indices, schemas, index_attr_list

async def etl_process(redis: Redis, elastic: AsyncElasticsearch):
    logging.info('Start')

    postgres_operator = PostgresDBOperator()

    for index in active_indices:
        await create_index(elastic=elastic, index_name=index, schema=schemas[index])

    logging.info("Set schema complete")

    while True:
        for index in active_indices:
            # получаем список изменений из БД
            pg_changes = postgres_operator.get_changes(index)
            if pg_changes:
                # преобразовываем изменения из БД в список обновлений для ES
                data_transformed = create_operations_list(data=pg_changes,
                                                          index_name=index,
                                                          index_attr_list=index_attr_list[index])
                # отправляем обновления в ES
                await add_data(elastic=elastic, index_name=index, data=data_transformed)
                # logging.info("Got new pack from db")
                await asyncio.sleep(1)
            else:
                logging.info(f"Nothing to update for index {index}")
                await asyncio.sleep(5)


async def create_index(elastic: AsyncElasticsearch, index_name: str, schema: str) -> None:
    if not await elastic.indices.exists(index=index_name):
        response = await elastic.indices.create(index=index_name, body=schema)
        logging.info(f"Index created: {response['acknowledged']}")
    else:
        logging.info(f"Index {index_name} already exists")

async def add_data(elastic: AsyncElasticsearch, index_name: str, data: list[dict]) -> None:
    await elastic.bulk(index=index_name, operations=data)

# собираем список обновлений для ES
def create_operations_list(data: list, index_name: str, index_attr_list: list) -> list[dict]:
    operations = []
    for item in data:
        operations.append({'index':{'_index': index_name, '_id': item['id']}})
        operations.append({attr: item[attr] for attr in index_attr_list})
    return operations