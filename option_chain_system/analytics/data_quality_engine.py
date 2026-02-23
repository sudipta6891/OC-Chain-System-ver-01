"""
Data quality guardrails for option-chain snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import pandas as pd


@dataclass
class DataQualityResult:
    is_usable: bool
    stale_data: bool
    missing_strikes: bool
    anomaly_flags: list[str]
    warnings: list[str]


class DataQualityEngine:
    @staticmethod
    def _get_strike_step(symbol: str) -> int:
        upper = symbol.upper()
        if "NIFTY50" in upper or "NIFTY-INDEX" in upper:
            return 50
        if "BANKNIFTY" in upper:
            return 100
        if "SENSEX" in upper:
            return 100
        return 100

    @staticmethod
    def assess(
        symbol: str,
        df: pd.DataFrame,
        spot: float,
        snapshot_time: datetime,
        max_stale_minutes: int = 12,
    ) -> DataQualityResult:
        warnings: list[str] = []
        anomaly_flags: list[str] = []

        if df.empty:
            return DataQualityResult(
                is_usable=False,
                stale_data=False,
                missing_strikes=True,
                anomaly_flags=["empty_snapshot"],
                warnings=["Option chain is empty."],
            )

        # Stale data guardrail
        now = datetime.now(snapshot_time.tzinfo) if snapshot_time.tzinfo else datetime.now()
        age = now - snapshot_time
        stale_data = age > timedelta(minutes=max_stale_minutes)
        if stale_data:
            warnings.append(f"Snapshot is stale by {int(age.total_seconds() // 60)} minutes.")

        # Basic anomaly checks
        if (df["strike_price"] <= 0).any():
            anomaly_flags.append("invalid_strike_price")
        if (df["open_interest"] < 0).any():
            anomaly_flags.append("negative_open_interest")
        if (df["volume"] < 0).any():
            anomaly_flags.append("negative_volume")
        if df[["strike_price", "option_type"]].duplicated().any():
            anomaly_flags.append("duplicate_strike_option_rows")

        for col in ("open_interest", "oi_change", "volume", "ltp"):
            numeric = pd.to_numeric(df[col], errors="coerce")
            if numeric.isna().mean() > 0.2:
                anomaly_flags.append(f"high_na_ratio_{col}")
            if math.isinf(float(numeric.fillna(0).abs().sum())):
                anomaly_flags.append(f"inf_detected_{col}")

        # Missing strike continuity check around ATM
        strikes = sorted(float(x) for x in df["strike_price"].dropna().unique())
        step = DataQualityEngine._get_strike_step(symbol)
        atm = min(strikes, key=lambda s: abs(s - spot)) if strikes else spot
        lower = atm - step * 8
        upper = atm + step * 8
        near = [s for s in strikes if lower <= s <= upper]
        expected = set(range(int(lower), int(upper + step), step))
        actual = set(int(round(s / step) * step) for s in near)
        missing_count = len(expected - actual)
        missing_strikes = missing_count > 3
        if missing_strikes:
            warnings.append(f"Missing strikes near ATM: {missing_count} gaps detected.")

        critical_flags = {
            "empty_snapshot",
            "invalid_strike_price",
            "negative_open_interest",
            "negative_volume",
        }
        is_usable = (not stale_data) and (not missing_strikes) and not (critical_flags & set(anomaly_flags))

        return DataQualityResult(
            is_usable=is_usable,
            stale_data=stale_data,
            missing_strikes=missing_strikes,
            anomaly_flags=anomaly_flags,
            warnings=warnings,
        )

