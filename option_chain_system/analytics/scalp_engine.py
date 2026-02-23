"""
Advanced OTM Scalp Engine (10-Min)

Includes:
- Directional weighted score
- Risk classification
- Bullish (+) / Bearish (-) conviction
"""

class OTMScalpEngine:

    @staticmethod
    def generate_signal(
        breakout_signal: str,
        covering_signal: str,
        volume_data: dict,
        prob_data: dict
    ) -> dict:

        breakdown = {
            "breakout": 0,
            "volume": 0,
            "bias": 0,
            "covering": 0
        }

        direction = 0  # +1 bullish, -1 bearish

        # -------------------------
        # Breakout Strength
        # -------------------------
        if breakout_signal == "Bullish Breakout":
            breakdown["breakout"] = 30
            direction = 1
        elif breakout_signal == "Bearish Breakdown":
            breakdown["breakout"] = -30
            direction = -1

        # -------------------------
        # Volume Expansion
        # -------------------------
        if volume_data.get("spike"):
            if direction != 0:
                breakdown["volume"] = 20 * direction

        # -------------------------
        # Bias Strength
        # -------------------------
        if prob_data["upside_probability"] >= 65:
            breakdown["bias"] = 20
            direction = 1
        elif prob_data["downside_probability"] >= 65:
            breakdown["bias"] = -20
            direction = -1
        elif prob_data["upside_probability"] >= 55:
            breakdown["bias"] = 10
            direction = 1
        elif prob_data["downside_probability"] >= 55:
            breakdown["bias"] = -10
            direction = -1

        # -------------------------
        # Short Covering
        # -------------------------
        if "Bullish" in covering_signal:
            breakdown["covering"] = 10
            direction = 1
        elif "Bearish" in covering_signal:
            breakdown["covering"] = -10
            direction = -1

        total_score = sum(breakdown.values())

        abs_score = abs(total_score)

        # -------------------------
        # Signal Classification
        # -------------------------
        if abs_score >= 70:
            signal = "STRONG BUY OTM"
            edge = "HIGH EDGE"
        elif abs_score >= 50:
            signal = "BUY OTM"
            edge = "MEDIUM EDGE"
        else:
            signal = "NO TRADE"
            edge = "LOW EDGE"

        # -------------------------
        # Risk Level
        # -------------------------
        if abs_score >= 70:
            risk = "MODERATE RISK"
        elif abs_score >= 50:
            risk = "HIGH RISK"
        else:
            risk = "AVOID TRADE"

        # -------------------------
        # Direction Label
        # -------------------------
        if total_score > 0:
            trade_direction = "BULLISH"
        elif total_score < 0:
            trade_direction = "BEARISH"
        else:
            trade_direction = "NEUTRAL"

        return {
            "signal": signal,
            "score": total_score,  # now directional
            "abs_score": abs_score,
            "direction": trade_direction,
            "edge": edge,
            "risk": risk,
            "breakdown": breakdown
        }