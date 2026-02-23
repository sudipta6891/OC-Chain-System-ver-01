"""
Market regime engine v2.
"""

from __future__ import annotations

import pandas as pd


class MarketRegimeEngine:
    @staticmethod
    def _atr_proxy(spots: pd.Series) -> float:
        if len(spots) < 3:
            return 0.0
        returns = spots.diff().abs().dropna()
        return float(returns.tail(12).mean() or 0.0)

    @staticmethod
    def _iv_percentile(df: pd.DataFrame) -> float:
        for col in ("iv", "implied_volatility", "impliedVolatility"):
            if col in df.columns:
                iv = pd.to_numeric(df[col], errors="coerce").dropna()
                if iv.empty:
                    continue
                v = iv.median()
                if v > 1.5:
                    v = v / 100.0
                # local percentile proxy against practical range 10% to 45%
                pct = (v - 0.10) / max(0.01, 0.45 - 0.10)
                return max(0.0, min(1.0, float(pct)))
        return 0.45

    @staticmethod
    def _breadth(df: pd.DataFrame, spot: float) -> float:
        if df.empty:
            return 0.0
        near = df[(df["strike_price"] >= spot * 0.98) & (df["strike_price"] <= spot * 1.02)]
        if near.empty:
            near = df
        ce_vol = near.loc[near["option_type"] == "CE", "volume"].sum()
        pe_vol = near.loc[near["option_type"] == "PE", "volume"].sum()
        tot = ce_vol + pe_vol
        if tot == 0:
            return 0.0
        return float((ce_vol - pe_vol) / tot)

    @staticmethod
    def detect(
        summary_history: pd.DataFrame,
        option_df: pd.DataFrame,
        oi_delta_data: dict,
    ) -> dict:
        if summary_history.empty:
            return {
                "label": "UNKNOWN",
                "confidence": 0,
                "features": {},
                "why_now": ["Insufficient summary history"],
                "why_not_now": ["No historical context to classify regime"],
            }

        spots = pd.to_numeric(summary_history["spot_price"], errors="coerce").dropna()
        pcr_series = pd.to_numeric(summary_history["pcr"], errors="coerce").dropna()
        atr = MarketRegimeEngine._atr_proxy(spots)
        avg_spot = float(spots.tail(12).mean() or spots.iloc[-1])
        atr_pct = (atr / max(1.0, avg_spot)) * 100
        iv_pct = MarketRegimeEngine._iv_percentile(option_df)
        breadth = MarketRegimeEngine._breadth(option_df, avg_spot)
        oi_acc = int(oi_delta_data.get("acceleration_probability", 0))

        if len(spots) >= 5:
            trend_slope = float(spots.tail(5).iloc[-1] - spots.tail(5).iloc[0])
        else:
            trend_slope = 0.0

        pcr_vol = float(pcr_series.tail(8).std() or 0.0) if len(pcr_series) >= 2 else 0.0

        label = "RANGE"
        confidence = 50
        why_now: list[str] = []
        why_not_now: list[str] = []

        if atr_pct > 0.55 and abs(trend_slope) > avg_spot * 0.003:
            label = "TREND"
            confidence = min(90, int(55 + abs(trend_slope) / max(1.0, avg_spot) * 10000))
            why_now.append("Range expansion with directional slope confirms trend regime.")
        elif atr_pct > 0.75 and pcr_vol > 0.15:
            label = "VOLATILE"
            confidence = min(90, int(50 + atr_pct * 30))
            why_now.append("High ATR proxy and unstable positioning indicate volatile regime.")
        elif oi_acc >= 65 and iv_pct > 0.70:
            label = "TRAP"
            confidence = min(85, int(45 + oi_acc * 0.5))
            why_now.append("High OI acceleration with elevated IV often precedes trap moves.")
        else:
            label = "RANGE"
            confidence = min(85, int(45 + (1 - min(1.0, atr_pct)) * 30))
            why_now.append("Contained ATR proxy and muted slope indicate range behavior.")

        if iv_pct > 0.8:
            why_not_now.append("IV is elevated; OTM long premium is expensive.")
        if abs(breadth) < 0.08:
            why_not_now.append("Volume breadth is weak; confirmation is limited.")
        if oi_acc < 35:
            why_not_now.append("OI acceleration is low; move persistence risk is higher.")

        return {
            "label": label,
            "confidence": confidence,
            "features": {
                "atr_proxy": round(atr, 2),
                "atr_pct": round(atr_pct, 4),
                "iv_percentile": round(iv_pct, 4),
                "breadth": round(breadth, 4),
                "oi_acceleration_probability": oi_acc,
                "trend_slope": round(trend_slope, 2),
                "pcr_volatility": round(pcr_vol, 4),
            },
            "why_now": why_now,
            "why_not_now": why_not_now,
        }

