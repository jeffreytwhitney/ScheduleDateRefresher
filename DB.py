from typing import List, Dict, Any

import pymssql


class DatabaseConnection:
    DB_SERVER = 'x'
    DB_USER = 'y'
    DB_PASSWORD = 'z'
    DB_NAME = 'a'

    def __init__(self, is_scalar: bool = False):
        self.conn = None
        self.cursor = None
        self.is_scalar = is_scalar

    def __enter__(self):
        if self.is_scalar:
            self.conn = pymssql.connect(
                server=self.DB_SERVER,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                database=self.DB_NAME,
                as_dict=False)
        else:
            self.conn = pymssql.connect(
                server=self.DB_SERVER,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                database=self.DB_NAME,
                as_dict=True)

        self.cursor = self.conn.cursor()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def fetch_records(self, sql: str) -> List[Dict[str, Any]]:
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def fetch_scalar(self, sql: str) -> Any:
        self.cursor.execute(sql)
        return self.cursor.fetchone()[0]

    def execute_statement(self, sql: str) -> None:
        self.cursor.execute(sql)
        self.conn.commit()


def get_sql_recordset(sql: str) -> List[Dict[str, Any]]:
    with DatabaseConnection(False) as db:
        return db.fetch_records(sql)


def get_sql_scalar(sql: str) -> Any:
    with DatabaseConnection(True) as db:
        return db.fetch_scalar(sql)


def execute_sql_statement(sql: str) -> None:
    with DatabaseConnection(False) as db:
        db.execute_statement(sql)
