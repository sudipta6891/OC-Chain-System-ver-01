"""
Database cleanup manager.
"""

from datetime import datetime, timedelta
from database.db_connection import DatabaseConnection
from config.settings import settings


class CleanupManager:
    @staticmethod
    def cleanup_old_data():
        retention_days = settings.DATA_RETENTION_DAYS
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        tables = [
            ("option_chain_snapshot", "snapshot_time"),
            ("option_chain_summary", "snapshot_time"),
            ("scalp_score_tracking", "snapshot_time"),
            ("trade_signals", "snapshot_time"),
            ("trade_outcomes", "created_at"),
        ]

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            for table, column in tables:
                cursor.execute(f"DELETE FROM {table} WHERE {column} < %s", (cutoff_date,))
                print(f"Cleaned old data from {table}")
            conn.commit()
        except Exception as e:
            conn.rollback()
            print("Cleanup failed:", e)
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

