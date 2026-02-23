"""
OTM timing score engine v2 with hard filters and calibration-ready output.
"""

from __future__ import annotations


class OTMTimingEngineV2:
    @staticmethod
    def score(
        geeks_data: dict,
        regime_data: dict,
        quality_data: dict,
        market_bias_data: dict,
    ) -> dict:
        g = geeks_data or {}
        m = market_bias_data or {}
        regime = (regime_data or {}).get("label", "UNKNOWN")
        q = quality_data or {}

        timing = 50
        reasons: list[str] = []
        blockers: list[str] = []

        directional = int(g.get("directional_score", 0))
        geeks_timing = int(g.get("otm_timing_score", 0))
        bias_conf = int(m.get("confidence", 0))
        market_score = int(m.get("market_score", 0))

        timing += int(0.30 * geeks_timing)
        timing += int(0.15 * abs(market_score))
        timing += int(0.10 * bias_conf)

        if regime == "TREND":
            timing += 10
            reasons.append("Trend regime supports momentum continuation.")
        elif regime == "RANGE":
            timing -= 6
            reasons.append("Range regime reduces OTM breakout edge.")
        elif regime == "VOLATILE":
            timing -= 4
            reasons.append("Volatile regime increases whipsaw risk.")
        elif regime == "TRAP":
            timing -= 12
            reasons.append("Trap regime raises false-breakout probability.")

        if q.get("stale_data"):
            blockers.append("Data is stale.")
        if q.get("missing_strikes"):
            blockers.append("Missing strike continuity near ATM.")
        if q.get("anomaly_flags"):
            blockers.append("Anomalies detected in option chain.")

        if abs(directional) < 15:
            blockers.append("Directional conviction too low.")

        if geeks_timing < 45:
            blockers.append("Greeks timing quality too low.")

        timing = max(0, min(100, int(timing)))
        allow_trade = len(blockers) == 0 and timing >= 55
        entry_window = (
            "FAVORABLE" if allow_trade and timing >= 70
            else "SELECTIVE" if allow_trade
            else "WAIT"
        )

        calibrated_raw = max(0.01, min(0.99, 0.5 + (market_score / 200.0)))
        expected_move_pct = max(0.10, min(2.20, 0.15 + (abs(market_score) * 0.015)))
        invalidation_pct = max(0.20, min(1.20, expected_move_pct * 0.45))

        return {
            "timing_score_v2": timing,
            "allow_trade": allow_trade,
            "entry_window": entry_window,
            "reasons": reasons,
            "blockers": blockers,
            "calibration_input_probability": calibrated_raw,
            "expected_move_pct": round(expected_move_pct, 3),
            "invalidation_pct": round(invalidation_pct, 3),
        }

