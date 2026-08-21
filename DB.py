import os
from typing import List, Dict, Any

import pymssql
from dotenv import load_dotenv

load_dotenv()


class DatabaseConnection:
    DB_SERVER = os.getenv('DB_SERVER', '')
    DB_USER = os.getenv('DB_USER', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', '')

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

    def execute_stored_procedure(self, procedure_name: str, params: tuple[Any, ...] | None = None) -> None:
        self.cursor.callproc(procedure_name, params or ())
        self.conn.commit()


class WindowsAuthDatabaseConnection:
    """Database connection class that uses Windows authentication."""
    
    DB_SERVER = os.getenv('DB_SERVER', '')

    def __init__(self, database_name: str, is_scalar: bool = False):
        """
        Initialize the connection with Windows authentication.
        
        Args:
            database_name: The name of the database to connect to
            is_scalar: If True, returns results as tuples; if False, returns as dictionaries
        """
        self.database_name = database_name
        self.conn = None
        self.cursor = None
        self.is_scalar = is_scalar

    def __enter__(self):
        # Windows authentication is used when user and password are not provided
        self.conn = pymssql.connect(
            server=self.DB_SERVER,
            database=self.database_name,
            as_dict=not self.is_scalar)

        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def fetch_records(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a query and return all records."""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def fetch_scalar(self, sql: str) -> Any:
        """Execute a query and return a single scalar value."""
        self.cursor.execute(sql)
        return self.cursor.fetchone()[0]

    def execute_statement(self, sql: str) -> None:
        """Execute a SQL statement (INSERT, UPDATE, DELETE, etc.)."""
        self.cursor.execute(sql)
        self.conn.commit()

    def execute_stored_procedure(self, procedure_name: str, params: tuple[Any, ...] | None = None) -> None:
        """Execute a stored procedure using Windows authentication."""
        self.cursor.callproc(procedure_name, params or ())
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


def execute_stored_procedure(procedure_name: str, params: tuple[Any, ...] | None = None) -> None:
    with DatabaseConnection(False) as db:
        db.execute_stored_procedure(procedure_name, params)


def get_sql_recordset_windows_auth(database_name: str, sql: str) -> List[Dict[str, Any]]:
    """Execute a query with Windows authentication and return all records."""
    with WindowsAuthDatabaseConnection(database_name, is_scalar=False) as db:
        return db.fetch_records(sql)


def get_sql_scalar_windows_auth(database_name: str, sql: str) -> Any:
    """Execute a query with Windows authentication and return a single scalar value."""
    with WindowsAuthDatabaseConnection(database_name, is_scalar=True) as db:
        return db.fetch_scalar(sql)


def execute_sql_statement_windows_auth(database_name: str, sql: str) -> None:
    """Execute a SQL statement with Windows authentication."""
    with WindowsAuthDatabaseConnection(database_name, is_scalar=False) as db:
        db.execute_statement(sql)


def execute_stored_procedure_windows_auth(
        database_name: str,
        procedure_name: str,
        params: tuple[Any, ...] | None = None) -> None:
    """Execute a stored procedure with Windows authentication."""
    with WindowsAuthDatabaseConnection(database_name, is_scalar=False) as db:
        db.execute_stored_procedure(procedure_name, params)

