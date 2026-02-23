"""
Database Connection Module
Handles PostgreSQL connection pooling
"""

import psycopg2
from psycopg2 import pool
from config.settings import settings


class DatabaseConnection:
    """
    Manages PostgreSQL connection pool
    """

    _connection_pool = None

    @classmethod
    def initialize_pool(cls) -> None:
        """
        Initialize connection pool
        """

        if cls._connection_pool is None:

            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,
                10,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME
            )

    @classmethod
    def get_connection(cls):

        if cls._connection_pool is None:
            cls.initialize_pool()

        return cls._connection_pool.getconn()

    @classmethod
    def release_connection(cls, connection) -> None:
        cls._connection_pool.putconn(connection)

    @classmethod
    def close_all_connections(cls) -> None:
        if cls._connection_pool:
            cls._connection_pool.closeall()
