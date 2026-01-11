"""
PostgreSQL connection management optimized for t2.micro
"""
import psycopg2
import psycopg2.extras
import logging
from contextlib import contextmanager
from typing import Optional, Any

from ..config import config

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Lightweight database connection manager for t2.micro"""
    
    def __init__(self):
        self._connection: Optional[psycopg2.connection] = None
        self._connection_params = {
            'host': config.database.host,
            'port': config.database.port,
            'database': config.database.database,
            'user': config.database.username,
            'password': config.database.password,
            'cursor_factory': psycopg2.extras.RealDictCursor
        }
    
    def connect(self) -> Any:
        """Create database connection with t2.micro optimizations"""
        try:
            self._connection = psycopg2.connect(**self._connection_params)
            self._connection.autocommit = False
            logger.info("Database connection established")
            return self._connection
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    @property
    def connection(self) -> Any:
        """Get current connection, create if needed"""
        if not self._connection or self._connection.closed:
            self.connect()
        return self._connection
    
    @contextmanager
    def cursor(self):
        """Context manager for database cursor with automatic cleanup"""
        cursor = None
        try:
            cursor = self.connection.cursor()
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute SELECT query and return results"""
        with self.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_command(self, command: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE command and return affected rows"""
        with self.cursor() as cursor:
            cursor.execute(command, params)
            return cursor.rowcount

# Global database connection instance
db = DatabaseConnection()