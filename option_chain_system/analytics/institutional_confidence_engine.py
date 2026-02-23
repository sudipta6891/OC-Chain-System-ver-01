"""
Directional Institutional Positioning Confidence Engine
Measures conviction strength + direction of smart money
"""

class InstitutionalConfidenceEngine:

    @staticmethod
    def calculate_confidence(
        oi_delta_data: dict,
        prob_data: dict,
        volume_data: dict,
        scalp_data: dict
    ) -> dict:

        score = 0
        reasons = []
        direction = 0  # +1 bullish, -1 bearish

        # -----------------------------------------
        # 1️⃣ OI Delta Strength (Directional)
        # -----------------------------------------
        ce_delta = oi_delta_data.get("ce_delta", 0)
        pe_delta = oi_delta_data.get("pe_delta", 0)

        total_delta_strength = abs(ce_delta) + abs(pe_delta)
        oi_strength = min(total_delta_strength / 100000, 25)

        score += oi_strength

        if abs(pe_delta) > abs(ce_delta):
            direction = 1
        elif abs(ce_delta) > abs(pe_delta):
            direction = -1

        if oi_strength > 10:
            reasons.append("Strong OI Expansion")

        # -----------------------------------------
        # 2️⃣ Probability Bias Direction
        # -----------------------------------------
        bias = prob_data.get("bias", "Neutral")

        if bias == "Bullish":
            score += 20
            direction = 1
            reasons.append("Bullish Bias Alignment")
        elif bias == "Bearish":
            score += 20
            direction = -1
            reasons.append("Bearish Bias Alignment")

        # -----------------------------------------
        # 3️⃣ Volume Confirmation
        # -----------------------------------------
        if volume_data.get("spike"):
            score += 20
            reasons.append("Volume Spike Confirmed")

        # -----------------------------------------
        # 4️⃣ Breakout Confirmation
        # -----------------------------------------
        if scalp_data["signal"] in ["BUY OTM", "STRONG BUY OTM"]:
            score += 20
            reasons.append("Directional Setup Active")

        # -----------------------------------------
        # 5️⃣ Scalp Directional Weight
        # -----------------------------------------
        scalp_score = scalp_data.get("score", 0)
        score += abs(scalp_score) * 0.15

        if scalp_score > 0:
            direction = 1
        elif scalp_score < 0:
            direction = -1

        # -----------------------------------------
        # Cap Score
        # -----------------------------------------
        score = min(int(score), 100)

        # -----------------------------------------
        # Apply Direction to Score
        # -----------------------------------------
        directional_score = score if direction >= 0 else -score
        abs_score = abs(directional_score)

        # -----------------------------------------
        # Classification
        # -----------------------------------------
        if abs_score >= 75:
            level = "HIGH"
        elif abs_score >= 50:
            level = "MODERATE"
        elif abs_score >= 30:
            level = "LOW"
        else:
            level = "VERY LOW"

        # -----------------------------------------
        # Direction Label
        # -----------------------------------------
        if directional_score > 0:
            direction_label = "BULLISH INSTITUTIONAL BUILD-UP"
        elif directional_score < 0:
            direction_label = "BEARISH INSTITUTIONAL BUILD-UP"
        else:
            direction_label = "NEUTRAL POSITIONING"

        # -----------------------------------------
        # Explanatory Interpretation
        # -----------------------------------------
        if level == "HIGH":
            note = (
                "Strong institutional conviction detected. "
                "Aggressive build-up with directional alignment. "
                "High probability of sustained move."
            )
        elif level == "MODERATE":
            note = (
                "Institutional activity visible but not aggressive. "
                "Structured positioning. Monitor confirmation."
            )
        elif level == "LOW":
            note = (
                "Limited conviction from institutions. "
                "Range-bound environment likely."
            )
        else:
            note = (
                "Very weak institutional positioning. "
                "Low conviction environment. Avoid aggressive exposure."
            )

        return {
            "directional_score": directional_score,
            "abs_score": abs_score,
            "level": level,
            "direction": direction_label,
            "reasons": reasons,
            "note": note
        }