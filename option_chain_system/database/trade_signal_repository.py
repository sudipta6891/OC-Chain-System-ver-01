"""
Repository for trade signal persistence.
"""

from __future__ import annotations

from database.db_connection import DatabaseConnection


class TradeSignalRepository:
    @staticmethod
    def insert_signal(
        symbol: str,
        snapshot_time,
        side: str,
        strike_price: float,
        entry_ltp: float | None,
        spot_price: float,
        regime: str,
        signal_strength: float,
        timing_score: float,
        raw_probability: float,
        calibrated_probability: float,
        stop_loss_pct: float,
        target_pct: float,
        time_stop_min: int,
        execution_notes: str,
    ) -> int | None:
        query = """
        INSERT INTO trade_signals (
            symbol, snapshot_time, side, strike_price, entry_ltp, spot_price,
            regime, signal_strength, timing_score, raw_probability, calibrated_probability,
            stop_loss_pct, target_pct, time_stop_min, execution_notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                query,
                (
                    symbol,
                    snapshot_time,
                    side,
                    strike_price,
                    entry_ltp,
                    spot_price,
                    regime,
                    signal_strength,
                    timing_score,
                    raw_probability,
                    calibrated_probability,
                    stop_loss_pct,
                    target_pct,
                    time_stop_min,
                    execution_notes,
                ),
            )
            signal_id = cursor.fetchone()[0]
            conn.commit()
            return int(signal_id)
        except Exception:
            conn.rollback()
            return None
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)
