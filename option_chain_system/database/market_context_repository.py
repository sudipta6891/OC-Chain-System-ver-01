"""
Read-side repository for market context and backtesting.
"""

from __future__ import annotations

import pandas as pd
from database.db_connection import DatabaseConnection
from config.settings import settings


class MarketContextRepository:
    @staticmethod
    def fetch_open_oi_by_strike(symbol: str, upto_time, market_open_time: str = "09:15:00") -> pd.DataFrame:
        query = """
        WITH first_snap AS (
            SELECT snapshot_time
            FROM option_chain_snapshot
            WHERE symbol = %s
              AND (snapshot_time AT TIME ZONE %s)::date = (%s AT TIME ZONE %s)::date
              AND (snapshot_time AT TIME ZONE %s)::time >= %s::time
              AND snapshot_time <= %s
            ORDER BY snapshot_time ASC
            LIMIT 1
        )
        SELECT strike_price, option_type, open_interest,
               (SELECT snapshot_time FROM first_snap) AS baseline_snapshot_time
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND snapshot_time = (SELECT snapshot_time FROM first_snap)
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            tz_name = getattr(settings, "TIMEZONE", "Asia/Kolkata")
            cursor.execute(
                query,
                (
                    symbol,
                    tz_name,
                    upto_time,
                    tz_name,
                    tz_name,
                    market_open_time,
                    upto_time,
                    symbol,
                ),
            )
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(
                rows,
                columns=["strike_price", "option_type", "open_interest", "baseline_snapshot_time"],
            )
            df["strike_price"] = pd.to_numeric(df["strike_price"], errors="coerce")
            df["open_interest"] = pd.to_numeric(df["open_interest"], errors="coerce")
            return df.dropna(subset=["strike_price", "open_interest"]).reset_index(drop=True)
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_recent_summaries(symbol: str, upto_time, limit: int = 24) -> pd.DataFrame:
        query = """
        SELECT snapshot_time, spot_price, pcr, resistance, support, max_pain
        FROM option_chain_summary
        WHERE symbol = %s
          AND snapshot_time <= %s
        ORDER BY snapshot_time DESC
        LIMIT %s
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, upto_time, limit))
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(
                rows,
                columns=["snapshot_time", "spot_price", "pcr", "resistance", "support", "max_pain"],
            )
            df["spot_price"] = pd.to_numeric(df["spot_price"], errors="coerce")
            df["pcr"] = pd.to_numeric(df["pcr"], errors="coerce")
            return df.sort_values("snapshot_time").reset_index(drop=True)
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_option_snapshot(symbol: str, snapshot_time, tolerance_min: int = 5) -> pd.DataFrame:
        query = """
        SELECT strike_price, option_type, open_interest, oi_change, volume, ltp, snapshot_time
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND snapshot_time BETWEEN %s - (%s || ' minutes')::interval
                                AND %s + (%s || ' minutes')::interval
        ORDER BY ABS(EXTRACT(EPOCH FROM (snapshot_time - %s)))
        LIMIT 400
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                query,
                (symbol, snapshot_time, tolerance_min, snapshot_time, tolerance_min, snapshot_time),
            )
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(
                rows,
                columns=[
                    "strike_price",
                    "option_type",
                    "open_interest",
                    "oi_change",
                    "volume",
                    "ltp",
                    "snapshot_time",
                ],
            )
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_signals_for_range(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        query = """
        SELECT id, symbol, snapshot_time, side, strike_price, entry_ltp,
               stop_loss_pct, target_pct, time_stop_min
        FROM trade_signals
        WHERE symbol = %s
          AND snapshot_time::date BETWEEN %s::date AND %s::date
        ORDER BY snapshot_time ASC
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, start_date, end_date))
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(
                rows,
                columns=[
                    "id",
                    "symbol",
                    "snapshot_time",
                    "side",
                    "strike_price",
                    "entry_ltp",
                    "stop_loss_pct",
                    "target_pct",
                    "time_stop_min",
                ],
            )
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

