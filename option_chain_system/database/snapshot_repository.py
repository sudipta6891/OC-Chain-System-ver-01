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
    def _is_id_duplicate(exc: Exception) -> bool:
        msg = str(exc)
        return (
            getattr(exc, "pgcode", None) == "23505"
            and "option_chain_snapshot_pkey" in msg
        )

    @staticmethod
    def _reset_id_sequence(cursor) -> None:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('option_chain_snapshot', 'id'),
                COALESCE((SELECT MAX(id) FROM option_chain_snapshot), 0) + 1,
                false
            )
            """
        )

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
            if SnapshotRepository._is_id_duplicate(e):
                try:
                    # Auto-heal SERIAL sequence drift and retry once.
                    SnapshotRepository._reset_id_sequence(cursor)
                    conn.commit()
                    execute_values(cursor, insert_query, values)
                    conn.commit()
                    return
                except Exception as retry_exc:
                    conn.rollback()
                    raise RuntimeError(f"Snapshot insert failed after sequence reset: {retry_exc}")
            raise RuntimeError(f"Snapshot insert failed: {e}")

        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)
