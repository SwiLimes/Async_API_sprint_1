import asyncio
import json
import logging

from elasticsearch import AsyncElasticsearch

from etl.elasticsearch_loader import ElasticsearchLoader
from etl.transformer import Transformer
from etl.postgres_db_operator import PostgresDBOperator
from etl.indices_info import active_indices, schemas, index_attr_list


async def etl_process(elastic: AsyncElasticsearch):
    logging.info('Start')

    postgres_operator = PostgresDBOperator()
    transformer = Transformer()
    movies_loader = ElasticsearchLoader(elastic=elastic, index_name='movies')

    for index in active_indices:
        await create_index(elastic=elastic, index_name=index, schema=schemas[index])

    for index in active_indices:
        count = (await elastic.count(index=index))['count']
        if count == 0:
            postgres_operator.reset_index_state(index)
            logging.info(f'Reset ETL state for empty index {index}')

    logging.info("Set schema complete")

    while True:
        for index in active_indices:
            pg_changes = postgres_operator.get_changes(index)
            if pg_changes:
                if index == 'movies':
                    film_ids = [row['id'] for row in pg_changes]
                    rows = postgres_operator.get_films_enriched(film_ids)
                    docs = transformer.transform(rows)
                    await movies_loader.load(docs)
                else:
                    data_transformed = create_operations_list(
                        data=pg_changes,
                        index_name=index,
                        index_attr_list=index_attr_list[index],
                    )
                    await add_data(elastic=elastic, index_name=index, data=data_transformed)
                await asyncio.sleep(1)
            else:
                logging.info(f"Nothing to update for index {index}")
                await asyncio.sleep(5)


async def create_index(elastic: AsyncElasticsearch, index_name: str, schema: str) -> None:
    if not await elastic.indices.exists(index=index_name):
        response = await elastic.indices.create(index=index_name, body=json.loads(schema))
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