"""
Scalp score repository.
"""

from database.db_connection import DatabaseConnection


class ScalpRepository:
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
        try:
            cursor.execute(
                query,
                (
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
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print("Scalp score insert failed:", e)
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

