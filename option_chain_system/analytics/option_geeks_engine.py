"""
Option Greeks Style Analysis Engine

Purpose:
- Estimate Greeks from option-chain snapshot
- Build directional bias + OTM buying timing score
- Provide interpretable factors for report email
"""

from __future__ import annotations

from datetime import datetime, date
import math
import pandas as pd


class OptionGeeksEngine:

    @staticmethod
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def _norm_pdf(x: float) -> float:
        return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)

    @staticmethod
    def _parse_expiry(raw_expiry) -> date | None:
        if raw_expiry is None or (isinstance(raw_expiry, float) and math.isnan(raw_expiry)):
            return None

        if isinstance(raw_expiry, datetime):
            return raw_expiry.date()

        if isinstance(raw_expiry, date):
            return raw_expiry

        # FYERS/other APIs may provide epoch seconds/ms
        if isinstance(raw_expiry, (int, float)):
            value = int(raw_expiry)
            if value > 10_000_000_000:
                value = int(value / 1000)
            try:
                return datetime.fromtimestamp(value).date()
            except Exception:
                return None

        if isinstance(raw_expiry, str):
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(raw_expiry.strip(), fmt).date()
                except ValueError:
                    continue

        return None

    @staticmethod
    def _time_to_expiry_years(df: pd.DataFrame, snapshot_time: datetime | None) -> float:
        expiry_cols = [c for c in ("expiry", "expiry_date", "expiryDate", "exd") if c in df.columns]
        if not expiry_cols:
            return 3.0 / 365.0

        exp_col = expiry_cols[0]
        expiry_dates = [OptionGeeksEngine._parse_expiry(v) for v in df[exp_col].dropna().tolist()]
        expiry_dates = [d for d in expiry_dates if d is not None]

        if not expiry_dates:
            return 3.0 / 365.0

        nearest = min(expiry_dates)
        now_date = snapshot_time.date() if isinstance(snapshot_time, datetime) else datetime.now().date()
        dte = max((nearest - now_date).days, 1)
        return dte / 365.0

    @staticmethod
    def _infer_sigma(df: pd.DataFrame, spot: float, atm: float) -> float:
        # Prefer chain IV if available
        for iv_col in ("iv", "implied_volatility", "impliedVolatility"):
            if iv_col in df.columns:
                iv_series = pd.to_numeric(df[iv_col], errors="coerce").dropna()
                if not iv_series.empty:
                    iv = float(iv_series.median())
                    # If already in decimal keep as is, else convert %
                    if iv > 1.5:
                        iv = iv / 100.0
                    return max(0.08, min(1.0, iv))

        # Fallback: derive rough vol from ATM straddle price ratio
        try:
            atm_rows = df[df["strike_price"] == atm]
            ce = atm_rows[atm_rows["option_type"] == "CE"]["ltp"].iloc[0]
            pe = atm_rows[atm_rows["option_type"] == "PE"]["ltp"].iloc[0]
            straddle = float(ce) + float(pe)
            rough = max(0.10, min(0.60, straddle / max(spot, 1.0) * 3.5))
            return rough
        except Exception:
            return 0.20

    @staticmethod
    def _bs_greeks(
        spot: float,
        strike: float,
        time_years: float,
        sigma: float,
        option_type: str,
        rate: float = 0.05,
    ) -> dict:
        t = max(time_years, 1.0 / 3650.0)
        vol = max(sigma, 0.05)
        s = max(spot, 1e-6)
        k = max(strike, 1e-6)

        d1 = (math.log(s / k) + (rate + 0.5 * vol * vol) * t) / (vol * math.sqrt(t))
        d2 = d1 - vol * math.sqrt(t)

        nd1 = OptionGeeksEngine._norm_cdf(d1)
        nd2 = OptionGeeksEngine._norm_cdf(d2)
        pdf_d1 = OptionGeeksEngine._norm_pdf(d1)

        if option_type == "CE":
            delta = nd1
            theta = (
                -(s * pdf_d1 * vol) / (2 * math.sqrt(t))
                - rate * k * math.exp(-rate * t) * nd2
            ) / 365.0
        else:
            delta = nd1 - 1.0
            theta = (
                -(s * pdf_d1 * vol) / (2 * math.sqrt(t))
                + rate * k * math.exp(-rate * t) * OptionGeeksEngine._norm_cdf(-d2)
            ) / 365.0

        gamma = pdf_d1 / (s * vol * math.sqrt(t))
        vega = s * pdf_d1 * math.sqrt(t) / 100.0

        return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}

    @staticmethod
    def analyze(
        df: pd.DataFrame,
        spot: float,
        atm: float,
        breakout_signal: str,
        snapshot_time: datetime | None = None,
        profile: str = "aggressive",
    ) -> dict:
        if df.empty:
            return {
                "bias": "NEUTRAL",
                "directional_score": 0,
                "otm_timing_score": 0,
                "preferred_otm_side": "NO TRADE / WAIT",
                "entry_window": "No data",
                "profile": profile.upper(),
                "trade_allowed": False,
                "hard_filters_triggered": ["No option chain snapshot data"],
                "metrics": {},
                "drivers": ["Option chain snapshot is empty"],
            }

        work = df.copy()
        work["strike_price"] = pd.to_numeric(work["strike_price"], errors="coerce")
        work["open_interest"] = pd.to_numeric(work["open_interest"], errors="coerce").fillna(0.0)
        work["volume"] = pd.to_numeric(work["volume"], errors="coerce").fillna(0.0)

        time_years = OptionGeeksEngine._time_to_expiry_years(work, snapshot_time)
        sigma = OptionGeeksEngine._infer_sigma(work, spot, atm)

        greek_rows = []
        for _, row in work.iterrows():
            opt_type = str(row.get("option_type", ""))
            if opt_type not in ("CE", "PE"):
                continue
            k = float(row["strike_price"])
            g = OptionGeeksEngine._bs_greeks(
                spot=spot,
                strike=k,
                time_years=time_years,
                sigma=sigma,
                option_type=opt_type,
            )
            g["option_type"] = opt_type
            g["strike_price"] = k
            g["open_interest"] = float(row["open_interest"])
            g["volume"] = float(row["volume"])
            greek_rows.append(g)

        gdf = pd.DataFrame(greek_rows)
        if gdf.empty:
            return {
                "bias": "NEUTRAL",
                "directional_score": 0,
                "otm_timing_score": 0,
                "preferred_otm_side": "NO TRADE / WAIT",
                "entry_window": "Insufficient Greeks data",
                "profile": profile.upper(),
                "trade_allowed": False,
                "hard_filters_triggered": ["Unable to compute Greeks rows"],
                "metrics": {},
                "drivers": ["Unable to compute Greeks for chain rows"],
            }

        near_band = gdf[(gdf["strike_price"] >= atm - 3 * (abs(atm) * 0.002)) & (gdf["strike_price"] <= atm + 3 * (abs(atm) * 0.002))]
        if near_band.empty:
            near_band = gdf

        # OI weighted exposures
        delta_exposure = (near_band["delta"] * near_band["open_interest"]).sum()
        ce_gamma = (
            near_band[near_band["option_type"] == "CE"]["gamma"]
            * near_band[near_band["option_type"] == "CE"]["open_interest"]
        ).sum()
        pe_gamma = (
            near_band[near_band["option_type"] == "PE"]["gamma"]
            * near_band[near_band["option_type"] == "PE"]["open_interest"]
        ).sum()
        gamma_imbalance = pe_gamma - ce_gamma

        theta_abs_mean = float(near_band["theta"].abs().mean())
        vega_mean = float(near_band["vega"].mean())
        volume_ratio = float(
            near_band["volume"].sum() / max(1.0, gdf["volume"].sum())
        )

        profile_name = profile.strip().lower()
        if profile_name not in ("aggressive", "conservative"):
            profile_name = "aggressive"

        drivers = []
        directional = 0

        # Delta
        if delta_exposure > 0:
            directional += 18
            drivers.append("Net positive delta exposure near ATM (+18)")
        elif delta_exposure < 0:
            directional -= 18
            drivers.append("Net negative delta exposure near ATM (-18)")

        # Gamma imbalance
        if gamma_imbalance > 0:
            directional += 14
            drivers.append("Put-side gamma support stronger (+14)")
        elif gamma_imbalance < 0:
            directional -= 14
            drivers.append("Call-side gamma wall stronger (-14)")

        # Breakout context
        if breakout_signal == "Bullish Breakout":
            directional += 12
            drivers.append("Breakout confirmation supports CE side (+12)")
        elif breakout_signal == "Bearish Breakdown":
            directional -= 12
            drivers.append("Breakdown confirmation supports PE side (-12)")
        elif profile_name == "aggressive":
            # Aggressive mode allows pre-breakout positioning with smaller penalty
            directional -= 4
            drivers.append("No breakout confirmation yet (-4)")

        # Score clamp
        directional = max(-100, min(100, int(directional)))

        direction_threshold = 18 if profile_name == "aggressive" else 25

        if directional >= direction_threshold:
            bias = "BULLISH"
            side = "BUY CE OTM"
        elif directional <= -direction_threshold:
            bias = "BEARISH"
            side = "BUY PE OTM"
        else:
            bias = "NEUTRAL"
            side = "NO TRADE / WAIT"

        # Timing score for OTM buying quality
        timing = 55 if profile_name == "aggressive" else 50

        if sigma < 0.17:
            timing += 10
            drivers.append("Implied vol proxy is low: better for option buying (+10)")
        elif sigma > 0.31:
            timing -= 10
            drivers.append("Implied vol proxy is elevated: option buying expensive (-10)")

        if theta_abs_mean > 7.5:
            timing -= 12
            drivers.append("High theta decay around ATM (-12)")
        elif theta_abs_mean < 4.5:
            timing += 6
            drivers.append("Theta pressure manageable (+6)")

        if volume_ratio > 0.30:
            timing += 10
            drivers.append("Near-ATM liquidity participation is strong (+10)")
        else:
            timing -= 4
            drivers.append("Liquidity participation is moderate/low (-4)")

        if abs(directional) >= 30:
            timing += 8
            drivers.append("Directional conviction strong (+8)")
        elif abs(directional) < 12:
            timing -= 8
            drivers.append("Directional conviction weak (-8)")

        timing = max(0, min(100, int(timing)))

        if timing >= 68:
            entry_window = "FAVORABLE FOR OTM BUYING"
        elif timing >= 52:
            entry_window = "SELECTIVE ENTRY ONLY"
        else:
            entry_window = "AVOID / WAIT FOR BETTER SETUP"

        # Hard no-trade filters (even in aggressive mode)
        hard_filters_triggered = []

        if abs(directional) < 12:
            hard_filters_triggered.append("Directional score too weak (<12)")

        if timing < 45:
            hard_filters_triggered.append("Timing score too low (<45)")

        if sigma > 0.40:
            hard_filters_triggered.append("Volatility too high (sigma proxy > 0.40)")

        if theta_abs_mean > 9.5:
            hard_filters_triggered.append("Theta decay too high (theta abs mean > 9.5)")

        if volume_ratio < 0.18:
            hard_filters_triggered.append("Liquidity too low near ATM (volume ratio < 0.18)")

        if breakout_signal == "No Breakout" and abs(directional) < 20:
            hard_filters_triggered.append("No breakout + low directional conviction")

        trade_allowed = len(hard_filters_triggered) == 0
        if not trade_allowed:
            side = "NO TRADE / WAIT"
            entry_window = "HARD FILTER BLOCKED"

        return {
            "bias": bias,
            "directional_score": directional,
            "otm_timing_score": timing,
            "preferred_otm_side": side,
            "entry_window": entry_window,
            "profile": profile_name.upper(),
            "trade_allowed": trade_allowed,
            "hard_filters_triggered": hard_filters_triggered,
            "metrics": {
                "delta_exposure": round(float(delta_exposure), 2),
                "gamma_imbalance": round(float(gamma_imbalance), 6),
                "theta_abs_mean": round(theta_abs_mean, 4),
                "vega_mean": round(vega_mean, 4),
                "sigma_proxy": round(sigma, 4),
                "time_to_expiry_years": round(time_years, 4),
                "near_atm_volume_ratio": round(volume_ratio, 4),
            },
            "drivers": drivers,
        }
