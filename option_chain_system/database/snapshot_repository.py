"""
Snapshot Repository

Handles bulk insert of option chain snapshot
"""

from typing import List
import pandas as pd
from psycopg2.extras import execute_values
from database.db_connection import DatabaseConnection


class SnapshotRepository:

    @staticmethod
    def bulk_insert_snapshot(df: pd.DataFrame) -> None:
        """
        Bulk insert option chain snapshot
        """

        if df.empty:
            return

        insert_query = """
        INSERT INTO option_chain_snapshot (
            symbol,
            strike_price,
            option_type,
            open_interest,
            oi_change,
            volume,
            ltp,
            snapshot_time
        )
        VALUES %s
        """

        values: List[tuple] = list(
            df[
                [
                    "symbol",
                    "strike_price",
                    "option_type",
                    "open_interest",
                    "oi_change",
                    "volume",
                    "ltp",
                    "snapshot_time"
                ]
            ].itertuples(index=False, name=None)
        )

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            execute_values(cursor, insert_query, values)
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Snapshot insert failed: {e}")

        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)
