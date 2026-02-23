import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.append(os.path.dirname(__file__))
try:
    from database.db_connection import DatabaseConnection
except Exception:
    DatabaseConnection = None


@unittest.skipIf(DatabaseConnection is None, "db dependencies unavailable")
class TestDatabaseConnection(unittest.TestCase):
    @patch("database.db_connection.psycopg2.pool.SimpleConnectionPool")
    def test_initialize_pool_once(self, mock_pool):
        DatabaseConnection._connection_pool = None
        fake_pool = MagicMock()
        mock_pool.return_value = fake_pool

        DatabaseConnection.initialize_pool()
        DatabaseConnection.initialize_pool()

        mock_pool.assert_called_once()
        self.assertIs(DatabaseConnection._connection_pool, fake_pool)


if __name__ == "__main__":
    unittest.main()
