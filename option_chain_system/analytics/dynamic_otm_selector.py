"""
Dynamic OTM strike selector using delta, liquidity, skew, theta and momentum alignment.
"""

from __future__ import annotations

import pandas as pd
from analytics.option_geeks_engine import OptionGeeksEngine


class DynamicOTMSelector:
    @staticmethod
    def _target_delta_band(regime: str) -> tuple[float, float]:
        regime = (regime or "").upper()
        if regime == "TREND":
            return (0.18, 0.32)
        if regime == "VOLATILE":
            return (0.10, 0.22)
        if regime == "RANGE":
            return (0.12, 0.22)
        if regime == "TRAP":
            return (0.08, 0.18)
        return (0.15, 0.28)

    @staticmethod
    def select(
        df: pd.DataFrame,
        spot: float,
        atm: float,
        side: str,
        breakout_signal: str,
        regime: str,
        snapshot_time,
    ) -> dict:
        if df.empty or side not in ("CE", "PE"):
            return {"strike": None, "entry_ltp": None, "score": 0.0, "reasons": ["No eligible chain data."]}

        work = df.copy()
        work["strike_price"] = pd.to_numeric(work["strike_price"], errors="coerce")
        work["ltp"] = pd.to_numeric(work["ltp"], errors="coerce")
        work["volume"] = pd.to_numeric(work["volume"], errors="coerce").fillna(0.0)
        work["open_interest"] = pd.to_numeric(work["open_interest"], errors="coerce").fillna(0.0)
        work = work[(work["option_type"] == side) & work["ltp"].notna() & (work["ltp"] > 0)]
        if work.empty:
            return {"strike": None, "entry_ltp": None, "score": 0.0, "reasons": ["No tradable strikes found."]}

        if side == "CE":
            work = work[work["strike_price"] >= atm]
        else:
            work = work[work["strike_price"] <= atm]
        if work.empty:
            return {"strike": None, "entry_ltp": None, "score": 0.0, "reasons": ["No OTM strikes found."]}

        t = OptionGeeksEngine._time_to_expiry_years(df, snapshot_time)  # noqa: SLF001
        sigma = OptionGeeksEngine._infer_sigma(df, spot, atm)  # noqa: SLF001
        d_low, d_high = DynamicOTMSelector._target_delta_band(regime)

        # Estimate skew using CE/PE IV medians if available.
        skew = 0.0
        iv_col = next((c for c in ("iv", "implied_volatility", "impliedVolatility") if c in df.columns), None)
        if iv_col:
            ce_iv = pd.to_numeric(df[df["option_type"] == "CE"][iv_col], errors="coerce").median()
            pe_iv = pd.to_numeric(df[df["option_type"] == "PE"][iv_col], errors="coerce").median()
            if pd.notna(ce_iv) and pd.notna(pe_iv):
                if ce_iv > 1.5:
                    ce_iv = ce_iv / 100.0
                if pe_iv > 1.5:
                    pe_iv = pe_iv / 100.0
                skew = float(pe_iv - ce_iv)

        reasons: list[str] = []
        scored_rows = []
        vol_ref = float(work["volume"].quantile(0.7) or work["volume"].mean() or 1.0)
        oi_ref = float(work["open_interest"].quantile(0.7) or work["open_interest"].mean() or 1.0)

        for _, row in work.iterrows():
            strike = float(row["strike_price"])
            ltp = float(row["ltp"])
            g = OptionGeeksEngine._bs_greeks(  # noqa: SLF001
                spot=spot,
                strike=strike,
                time_years=t,
                sigma=sigma,
                option_type=side,
            )
            delta_abs = abs(float(g["delta"]))
            theta_abs = abs(float(g["theta"]))
            vega = float(g["vega"])

            delta_score = 1.0 - min(1.0, abs((delta_abs - (d_low + d_high) / 2.0)) / 0.20)
            liquidity_score = min(1.0, (float(row["volume"]) / max(1.0, vol_ref)) * 0.6 + (float(row["open_interest"]) / max(1.0, oi_ref)) * 0.4)
            theta_score = max(0.0, 1.0 - min(1.0, theta_abs / 9.0))
            skew_score = 0.5
            if side == "CE":
                skew_score = 1.0 if skew <= 0 else max(0.0, 1.0 - min(1.0, skew / 0.12))
            if side == "PE":
                skew_score = 1.0 if skew >= 0 else max(0.0, 1.0 - min(1.0, abs(skew) / 0.12))

            momentum_score = 0.5
            if breakout_signal == "Bullish Breakout" and side == "CE":
                momentum_score = 1.0
            elif breakout_signal == "Bearish Breakdown" and side == "PE":
                momentum_score = 1.0
            elif breakout_signal == "No Breakout":
                momentum_score = 0.35

            total = (
                0.32 * delta_score
                + 0.28 * liquidity_score
                + 0.18 * theta_score
                + 0.10 * skew_score
                + 0.12 * momentum_score
            )
            scored_rows.append(
                {
                    "strike": strike,
                    "ltp": ltp,
                    "score": total,
                    "delta_abs": delta_abs,
                    "theta_abs": theta_abs,
                    "vega": vega,
                }
            )

        picked = max(scored_rows, key=lambda x: x["score"])
        reasons.append(f"Selected strike with highest blended score ({picked['score']:.2f}).")
        reasons.append(f"Delta abs {picked['delta_abs']:.2f} in target regime band [{d_low:.2f}, {d_high:.2f}].")
        reasons.append(f"Theta abs {picked['theta_abs']:.2f} and liquidity considered.")

        return {
            "strike": picked["strike"],
            "entry_ltp": picked["ltp"],
            "score": round(float(picked["score"]) * 100, 2),
            "delta_abs": round(picked["delta_abs"], 4),
            "theta_abs": round(picked["theta_abs"], 4),
            "vega": round(picked["vega"], 4),
            "reasons": reasons,
        }

