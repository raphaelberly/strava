import logging
from datetime import timezone
from os import path

import pandas as pd
import psycopg2

LOGGER = logging.getLogger(__name__)
LOCAL_DIR = path.dirname(__file__)


class Database(object):

    def __init__(self, host, port, user, password, database, schema):
        self.schema = schema
        self._credentials = {'host': host, 'port': port, 'user': user, 'password': password, 'database': database}

    @staticmethod
    def _execute(query: str, conn):
        cur = conn.cursor()
        LOGGER.debug(query)
        cur.execute(query)
        return cur

    @property
    def last_activity_timestamp(self):
        with psycopg2.connect(**self._credentials) as conn:
            dt_utc, = self._execute(f'SELECT max(start_datetime_utc) FROM {self.schema}.activities', conn).fetchone()
        return dt_utc.replace(tzinfo=timezone.utc).timestamp()

    def run_query(self, query: str) -> pd.DataFrame:
        with psycopg2.connect(**self._credentials) as conn:
            cur = self._execute(query, conn)
            return pd.DataFrame(cur.fetchall(), columns=[desc[0] for desc in cur.description]).infer_objects()

    def table(self, table_name: str) -> pd.DataFrame:
        return self.run_query(f'SELECT * FROM {self.schema}.{table_name}')

    def insert(self, table_name: str, **kwargs):
        query = "INSERT INTO {schema}.{table} ({columns}) VALUES ('{values}');".format(
            schema=self.schema,
            table=table_name,
            columns=', '.join(list(kwargs.keys())),
            values="', '".join(list(map(str, kwargs.values())))
        )
        with psycopg2.connect(**self._credentials) as conn:
            self._execute(query, conn)
