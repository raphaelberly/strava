import logging
from contextlib import contextmanager
from datetime import timezone
from os import path
from typing import Optional

import pandas as pd
import psycopg2
from sshtunnel import SSHTunnelForwarder

LOGGER = logging.getLogger(__name__)
LOCAL_DIR = path.dirname(__file__)


@contextmanager
def get_conn(host, port, user, password, database, remote_host=None, remote_port=None, remote_username=None,
             local_port=None):
    _credentials = {'host': 'localhost', 'port': local_port, 'user': user, 'password': password, 'database': database}
    if remote_host is not None:
        assert remote_port is not None and remote_username is not None
        with SSHTunnelForwarder(
                # The private key must be saved in the computer's keychain: ssh-add -K ~/.ssh/[your-private-key]
                ssh_address_or_host=(remote_host, remote_port),
                ssh_username=remote_username,
                remote_bind_address=(host, port),
                local_bind_address=('localhost', local_port),
                host_pkey_directories=[],
        ):
            with psycopg2.connect(**_credentials) as conn:
                yield conn
    else:
        with psycopg2.connect(**_credentials) as conn:
            yield conn


class Database(object):

    def __init__(self, host, port, user, password, database, schema, remote_host=None, remote_port=None,
                 remote_username=None, local_port=None):
        self.schema = schema
        self._credentials = {'host': host, 'port': port, 'user': user, 'password': password, 'database': database,
                             'remote_host': remote_host, 'remote_port': remote_port, 'remote_username': remote_username,
                             'local_port': local_port}

    @staticmethod
    def _execute(query: str, conn):
        cur = conn.cursor()
        LOGGER.debug(query)
        cur.execute(query)
        return cur

    def run_query(self, query: str) -> pd.DataFrame:
        with get_conn(**self._credentials) as conn:
            cur = self._execute(query, conn)
            return pd.DataFrame(cur.fetchall(), columns=[desc[0] for desc in cur.description]).infer_objects()

    def last_activity_timestamp(self, table_name='activities', offset=0) -> Optional[float]:
        with get_conn(**self._credentials) as conn:
            query = f"""
                SELECT start_datetime_utc
                FROM {self.schema}.{table_name}
                ORDER BY start_datetime_utc DESC
                LIMIT 1 OFFSET {offset};
            """
            dt_utc, = self._execute(query, conn).fetchone()
        return dt_utc.replace(tzinfo=timezone.utc).timestamp() if dt_utc is not None else None

    def insert(self, table_name: str, **kwargs) -> None:
        query = "INSERT INTO {schema}.{table} ({columns}) VALUES ('{values}');".format(
            schema=self.schema,
            table=table_name,
            columns=', '.join(list(kwargs.keys())),
            values="','".join((str(val).replace("'", "''") for val in kwargs.values()))
        ).replace("'None'", "NULL")
        with get_conn(**self._credentials) as conn:
            self._execute(query, conn)

    def upsert(self, table_name: str, constraint_name: str, schema=None, **kwargs):
        query = "INSERT INTO {schema}.{table} ({columns}) VALUES ('{values}') " \
                "ON CONFLICT ON CONSTRAINT {constraint} DO UPDATE SET {updates};" \
            .format(
                schema=schema or self.schema,
                table=table_name,
                constraint=constraint_name,
                columns=', '.join(list(kwargs.keys())),
                values="','".join((str(v).replace("'", "''") for v in kwargs.values())),
                updates=", ".join([
                    "{k}='{v}'".format(k=k, v=str(v).replace("'", "''")) for k, v in kwargs.items()
                ])
            ).replace("'None'", "NULL")
        with get_conn(**self._credentials) as conn:
            return self._execute(query, conn)
