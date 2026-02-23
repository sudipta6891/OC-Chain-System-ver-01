"""
Intraday OI delta and acceleration engine.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
import pandas as pd
import pytz
from database.db_connection import DatabaseConnection


class IntradayOIDeltaEngine:
    @staticmethod
    def _get_strike_step(symbol: str) -> int:
        upper = symbol.upper()
        if "BANKNIFTY" in upper:
            return 100
        if "NIFTY" in upper:
            return 50
        if "SENSEX" in upper:
            return 100
        return 100

    @staticmethod
    def _get_atm_strike(df: pd.DataFrame, spot: float) -> float:
        strikes = df["strike_price"].unique()
        return min(strikes, key=lambda x: abs(x - spot))

    @staticmethod
    def _apply_atm_filter(
        current_df: pd.DataFrame,
        prev_df: pd.DataFrame,
        symbol: str,
        spot: float,
        range_size: int = 3,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        step = IntradayOIDeltaEngine._get_strike_step(symbol)
        atm = IntradayOIDeltaEngine._get_atm_strike(current_df, spot)
        lower = atm - (step * range_size)
        upper = atm + (step * range_size)

        filtered_current = current_df[
            (current_df["strike_price"] >= lower) & (current_df["strike_price"] <= upper)
        ]
        filtered_prev = prev_df[
            (prev_df["strike_price"] >= lower) & (prev_df["strike_price"] <= upper)
        ]
        return filtered_current, filtered_prev

    @staticmethod
    def _default_response(reason: str) -> dict:
        return {
            "ce_delta": 0,
            "pe_delta": 0,
            "classification": reason,
            "bullish_probability": 50,
            "bearish_probability": 50,
            "acceleration_direction": "N/A",
            "acceleration_probability": 0,
        }

    @staticmethod
    def _market_closed_response() -> dict:
        return IntradayOIDeltaEngine._default_response("Market Closed")

    @staticmethod
    def _fetch_snapshot_times(symbol: str, snapshot_time: datetime) -> list[datetime]:
        # Prevent future-data leakage by restricting to historical-or-current timestamps.
        query = """
        SELECT DISTINCT snapshot_time
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND snapshot_time <= %s
        ORDER BY snapshot_time DESC
        LIMIT 3
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, snapshot_time))
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_snapshot_by_time(symbol: str, snapshot_time: datetime) -> pd.DataFrame | None:
        query = """
        SELECT strike_price, option_type, open_interest
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND snapshot_time = %s
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, snapshot_time))
            rows = cursor.fetchall()
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=["strike_price", "option_type", "open_interest"])
            df["strike_price"] = df["strike_price"].astype(float)
            df["open_interest"] = df["open_interest"].astype(float)
            return df
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def calculate_oi_delta(symbol: str, snapshot_time: datetime, spot: float) -> dict:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = snapshot_time.astimezone(ist)
        if now_ist.weekday() >= 5:
            return IntradayOIDeltaEngine._market_closed_response()
        if not (time(9, 15) <= now_ist.time() <= time(15, 30)):
            return IntradayOIDeltaEngine._market_closed_response()

        times = IntradayOIDeltaEngine._fetch_snapshot_times(symbol, snapshot_time)
        if len(times) < 2:
            return IntradayOIDeltaEngine._default_response("No Previous Data")

        current_time = times[0]
        prev_time = times[1]
        if abs(current_time - prev_time) > timedelta(minutes=15):
            return IntradayOIDeltaEngine._default_response("Data Gap - Skip")

        current_df = IntradayOIDeltaEngine.fetch_snapshot_by_time(symbol, current_time)
        prev_df = IntradayOIDeltaEngine.fetch_snapshot_by_time(symbol, prev_time)
        if current_df is None or prev_df is None:
            return IntradayOIDeltaEngine._default_response("Snapshot Fetch Failed")

        current_df, prev_df = IntradayOIDeltaEngine._apply_atm_filter(
            current_df=current_df,
            prev_df=prev_df,
            symbol=symbol,
            spot=spot,
            range_size=3,
        )
        if current_df.empty or prev_df.empty:
            return IntradayOIDeltaEngine._default_response("ATM Filter Empty")

        current_df = current_df[["strike_price", "option_type", "open_interest"]].rename(
            columns={"open_interest": "oi_current"}
        )
        prev_df = prev_df[["strike_price", "option_type", "open_interest"]].rename(
            columns={"open_interest": "oi_prev"}
        )

        merged = pd.merge(current_df, prev_df, on=["strike_price", "option_type"], how="left")
        merged["oi_prev"] = merged["oi_prev"].fillna(0.0)
        merged["oi_delta"] = merged["oi_current"] - merged["oi_prev"]

        ce_delta = merged.loc[merged["option_type"] == "CE", "oi_delta"].sum()
        pe_delta = merged.loc[merged["option_type"] == "PE", "oi_delta"].sum()

        acceleration_direction = "N/A"
        acceleration_probability = 0
        if len(times) >= 3:
            prev_prev_time = times[2]
            prev_prev_df = IntradayOIDeltaEngine.fetch_snapshot_by_time(symbol, prev_prev_time)
            if prev_prev_df is not None:
                prev_prev_df = prev_prev_df.rename(columns={"open_interest": "oi_prev_prev"})
                prev_for_acc = prev_df.rename(columns={"oi_prev": "oi_current"})
                merged_prev = pd.merge(
                    prev_for_acc,
                    prev_prev_df[["strike_price", "option_type", "oi_prev_prev"]],
                    on=["strike_price", "option_type"],
                    how="left",
                )
                merged_prev["oi_prev_prev"] = merged_prev["oi_prev_prev"].fillna(0.0)
                merged_prev["oi_delta_prev"] = merged_prev["oi_current"] - merged_prev["oi_prev_prev"]

                prev_ce_delta = merged_prev.loc[merged_prev["option_type"] == "CE", "oi_delta_prev"].sum()
                prev_pe_delta = merged_prev.loc[merged_prev["option_type"] == "PE", "oi_delta_prev"].sum()
                ce_acc = ce_delta - prev_ce_delta
                pe_acc = pe_delta - prev_pe_delta
                total_acc = abs(ce_acc) + abs(pe_acc)
                if total_acc > 0:
                    if abs(pe_acc) > abs(ce_acc):
                        acceleration_direction = "Bullish Acceleration"
                        acceleration_probability = int(abs(pe_acc) / total_acc * 100)
                    else:
                        acceleration_direction = "Bearish Acceleration"
                        acceleration_probability = int(abs(ce_acc) / total_acc * 100)

        total_activity = abs(ce_delta) + abs(pe_delta)
        if total_activity == 0:
            bullish_probability = 50
            bearish_probability = 50
        else:
            bullish_strength = max(pe_delta, 0) + abs(min(ce_delta, 0))
            bullish_probability = int(bullish_strength / total_activity * 100)
            bearish_probability = 100 - bullish_probability

        if ce_delta > 0 and pe_delta < 0:
            classification = "Call Writing Dominant"
        elif pe_delta > 0 and ce_delta < 0:
            classification = "Put Writing Dominant"
        elif ce_delta < 0 and pe_delta < 0:
            classification = "Short Covering Both Sides"
        elif ce_delta > 0 and pe_delta > 0:
            classification = "Straddle/Strangle Build-Up"
        else:
            classification = "Mixed Activity"

        return {
            "ce_delta": int(ce_delta),
            "pe_delta": int(pe_delta),
            "classification": classification,
            "bullish_probability": bullish_probability,
            "bearish_probability": bearish_probability,
            "acceleration_direction": acceleration_direction,
            "acceleration_probability": acceleration_probability,
        }

