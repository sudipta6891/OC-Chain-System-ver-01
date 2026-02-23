"""
Market Bias & Probability Engine
Generates directional probability score
"""

class ProbabilityEngine:

    @staticmethod
    def calculate_bias(
        pcr: float,
        breakout_signal: str,
        structure: str,
        calibration_probability: float | None = None,
    ) -> dict:

        score = 0

        # PCR weight
        if pcr > 1.2:
            score += 2
        elif pcr > 1.0:
            score += 1
        elif pcr < 0.8:
            score -= 2
        elif pcr < 1.0:
            score -= 1

        # Breakout weight
        if breakout_signal == "Bullish Breakout":
            score += 2
        elif breakout_signal == "Bearish Breakdown":
            score -= 2

        # Structure weight
        if "Put Writing" in structure:
            score += 1
        elif "Call Writing" in structure:
            score -= 1

        # Convert score to probabilities
        upside_prob = 50 + (score * 10)
        downside_prob = 100 - upside_prob

        # Clamp between 0–100
        upside_prob = max(0, min(100, upside_prob))
        downside_prob = max(0, min(100, downside_prob))

        if upside_prob > downside_prob:
            bias = "Bullish"
        elif downside_prob > upside_prob:
            bias = "Bearish"
        else:
            bias = "Neutral"

        breakout_probability = abs(score) * 10
        calibrated = calibration_probability if calibration_probability is not None else (upside_prob / 100.0)

        return {
            "bias": bias,
            "upside_probability": upside_prob,
            "downside_probability": downside_prob,
            "breakout_probability": breakout_probability,
            "raw_score": score,
            "calibrated_upside_probability": round(max(0.0, min(1.0, calibrated)), 4),
        }
