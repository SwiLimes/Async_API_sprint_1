import logging

import backoff
from etl.etl_state import State, JsonFileStorage
from core import config
from etl.indices_info import active_indices, pg_extract_queries, state_attr_name_in_json

import os
from contextlib import closing
import psycopg
from psycopg import ClientCursor
from psycopg.rows import dict_row


class PostgresDBOperator:
    """
        Этот класс используется для взаимодействия с Postgres, получения изменений в БД,
        параметры подключения извлекаются из переменных среды
    """
    def __init__(self):
        self.state = State(JsonFileStorage(file_path=config.STATE_FILEPATH))

        # проверяем, на каком времени остановились в прошлый раз при загрузке данных в ES
        self.last_checked_ts = {idx: "1900-01-01 00:00:00" for idx in active_indices}
        for idx in active_indices:
            last_checked_ts_ = self.state.get_state(state_attr_name_in_json[idx])

            if not last_checked_ts_:
                self.last_checked_ts[idx] = "1900-01-01 00:00:00"
                self.state.set_state(state_attr_name_in_json[idx], self.last_checked_ts[idx])
                # datetime.datetime.strptime("1900-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")

        self.dsn = {
            "dbname": config.POSTGRES_DB,
            "user": config.POSTGRES_USER,
            "password": config.POSTGRES_PASSWORD,
            "host": config.POSTGRES_HOST,
            "port": config.POSTGRES_PORT,
            "options": "-c search_path=content",
        }


    @backoff.on_exception(backoff.expo, (psycopg.OperationalError, ConnectionError), max_tries=5)
    def get_changes(self, index="persons"):
        # logging.info(f"last_checked_ts = {str(self.last_checked_ts[index])}")
        with (closing(psycopg.connect(**self.dsn, row_factory=dict_row, cursor_factory=ClientCursor)) as pg_conn,
              pg_conn.cursor() as cursor):
            sql_query = """
                        WITH data AS (
                        {data_query}
                        )
                        
                        SELECT *
                        FROM data
                        WHERE modified > '{last_checked_ts}'::timestamp
                        ORDER BY modified ASC
                        LIMIT 250; 
                        """.format(last_checked_ts=self.last_checked_ts[index],
                                   data_query=pg_extract_queries[index])
            cursor.execute(sql_query)
            result = cursor.fetchall()
        if not result:
            return []
        # когда мы делаем срез по дате, может случиться так, что не все записи, обновлённые
        # в одну дату, попадут в батч размера 250 (или другого размера)
        # Поэтому берутся все даты, сортируются. Если их несколько, то берётся вторая.
        # Есть шанс, что записей с одинаковой датой обновления будет больше, поэтому решение ниже не спасёт.
        # Надо придумывать что-то другое
        last_modified_dates = sorted(set([a["modified"] for a in result]), reverse=True)
        if len(last_modified_dates) > 1:
            self.last_checked_ts[index] = last_modified_dates[1].strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            self.last_checked_ts[index] = last_modified_dates[0].strftime("%Y-%m-%d %H:%M:%S.%f")
        self.state.set_state(state_attr_name_in_json[index],
                             self.last_checked_ts[index])

        logging.info("{state_name_in_json} = {last_checked_ts}, out list len = {result_len}".format(
            state_name_in_json=state_attr_name_in_json[index],
            last_checked_ts=self.last_checked_ts[index],
            result_len=len(result)
        ))

        return result