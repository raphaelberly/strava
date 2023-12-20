import logging
from datetime import datetime, timezone
from os import path
from typing import Optional

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
    def last_activity_timestamp(self) -> Optional[datetime]:
        with psycopg2.connect(**self._credentials) as conn:
            dt_utc, = self._execute(f'SELECT max(start_datetime_utc) FROM {self.schema}.activities', conn).fetchone()
        return dt_utc.replace(tzinfo=timezone.utc).timestamp() if dt_utc is not None else None

    def insert(self, table_name: str, **kwargs) -> None:
        query = "INSERT INTO {schema}.{table} ({columns}) VALUES ('{values}');".format(
            schema=self.schema,
            table=table_name,
            columns=', '.join(list(kwargs.keys())),
            values="','".join((str(val).replace("'", "''") for val in kwargs.values()))
        ).replace("'None'", "NULL")
        with psycopg2.connect(**self._credentials) as conn:
            self._execute(query, conn)
