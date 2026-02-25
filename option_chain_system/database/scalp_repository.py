"""
Scalp score repository.
"""

from database.db_connection import DatabaseConnection


class ScalpRepository:
    @staticmethod
    def _is_id_duplicate(exc: Exception) -> bool:
        msg = str(exc)
        return (
            getattr(exc, "pgcode", None) == "23505"
            and "scalp_score_tracking_pkey" in msg
        )

    @staticmethod
    def _reset_id_sequence(cursor) -> None:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('scalp_score_tracking', 'id'),
                COALESCE((SELECT MAX(id) FROM scalp_score_tracking), 0) + 1,
                false
            )
            """
        )

    @staticmethod
    def insert_scalp_score(symbol: str, snapshot_time, spot_price: float, scalp_data: dict) -> None:
        query = """
        INSERT INTO scalp_score_tracking (
            symbol, snapshot_time, spot_price,
            breakout_score, volume_score, bias_score, covering_score,
            total_score, signal, edge, risk_level
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        params = (
            symbol,
            snapshot_time,
            spot_price,
            scalp_data["breakdown"]["breakout"],
            scalp_data["breakdown"]["volume"],
            scalp_data["breakdown"]["bias"],
            scalp_data["breakdown"]["covering"],
            scalp_data["score"],
            scalp_data["signal"],
            scalp_data["edge"],
            scalp_data["risk"],
        )
        try:
            cursor.execute(query, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            if ScalpRepository._is_id_duplicate(e):
                try:
                    # Auto-heal SERIAL sequence drift and retry once.
                    ScalpRepository._reset_id_sequence(cursor)
                    conn.commit()
                    cursor.execute(query, params)
                    conn.commit()
                    return
                except Exception as retry_exc:
                    conn.rollback()
                    print("Scalp score insert failed after sequence reset:", retry_exc)
                    return
            print("Scalp score insert failed:", e)
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

