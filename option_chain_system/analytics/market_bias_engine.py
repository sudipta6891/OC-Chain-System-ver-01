"""
Multi-Factor Market Bias Engine

Purpose:
- Build directional bias from multiple option-chain signals
- Produce confidence and OTM buying suitability scores
"""


class MarketBiasEngine:

    @staticmethod
    def _score_to_bias_label(score: int) -> str:
        if score >= 45:
            return "STRONG BULLISH"
        if score >= 20:
            return "BULLISH"
        if score <= -45:
            return "STRONG BEARISH"
        if score <= -20:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def calculate_market_bias(
        pcr: float,
        structure: str,
        breakout_signal: str,
        trap: str,
        spot: float,
        support: float,
        resistance: float,
        max_pain: float,
        prob_data: dict,
        volume_data: dict,
        oi_delta_data: dict,
        scalp_data: dict
    ) -> dict:

        score = 0
        factors = []

        # 1) PCR directional context
        if pcr >= 1.4:
            score += 16
            factors.append("PCR high: bullish put-writer dominance (+16)")
        elif pcr >= 1.15:
            score += 10
            factors.append("PCR supportive for upside (+10)")
        elif pcr <= 0.7:
            score -= 16
            factors.append("PCR very low: bearish call-writer dominance (-16)")
        elif pcr <= 0.9:
            score -= 10
            factors.append("PCR weak for upside (-10)")

        # 2) Structure weight
        if "Put Writing" in structure:
            score += 10
            factors.append("Put writing structure (+10)")
        elif "Call Writing" in structure:
            score -= 10
            factors.append("Call writing structure (-10)")

        # 3) Breakout/Breakdown + trap
        if breakout_signal == "Bullish Breakout":
            score += 20
            factors.append("Bullish breakout (+20)")
        elif breakout_signal == "Bearish Breakdown":
            score -= 20
            factors.append("Bearish breakdown (-20)")

        if "Call Trap" in trap:
            score -= 8
            factors.append("Call trap risk (-8)")
        elif "Put Trap" in trap:
            score += 8
            factors.append("Put trap risk (+8)")

        # 4) Probability model
        upside_prob = prob_data.get("upside_probability", 50)
        downside_prob = prob_data.get("downside_probability", 50)
        prob_edge = upside_prob - downside_prob
        prob_points = max(-15, min(15, int(round(prob_edge * 0.3))))
        score += prob_points
        if prob_points != 0:
            factors.append(f"Probability edge ({prob_points:+d})")

        # 5) Intraday OI delta probability
        oi_bull = oi_delta_data.get("bullish_probability", 50)
        oi_bear = oi_delta_data.get("bearish_probability", 50)
        oi_edge = oi_bull - oi_bear
        oi_points = max(-15, min(15, int(round(oi_edge * 0.3))))
        score += oi_points
        if oi_points != 0:
            factors.append(f"OI delta directional edge ({oi_points:+d})")

        # 6) ATM volume direction
        if volume_data.get("ce_spike") and not volume_data.get("pe_spike"):
            score += 7
            factors.append("ATM CE volume expansion (+7)")
        elif volume_data.get("pe_spike") and not volume_data.get("ce_spike"):
            score -= 7
            factors.append("ATM PE volume expansion (-7)")
        elif volume_data.get("spike"):
            factors.append("Bidirectional ATM volume spike (neutral)")

        # 7) Proximity context: support/resistance and max pain
        level_range = max(1.0, resistance - support)
        relative_pos = (spot - support) / level_range
        if relative_pos >= 0.75:
            score += 5
            factors.append("Spot near upper range (+5)")
        elif relative_pos <= 0.25:
            score -= 5
            factors.append("Spot near lower range (-5)")

        maxpain_diff_pct = abs(spot - max_pain) / max(1.0, spot) * 100
        if maxpain_diff_pct <= 0.15:
            score = int(score * 0.9)
            factors.append("Spot near max pain: trend confidence reduced (x0.9)")

        # 8) Scalp engine directional conviction (limited influence)
        scalp_score = scalp_data.get("score", 0)
        scalp_points = max(-12, min(12, int(round(scalp_score * 0.2))))
        score += scalp_points
        if scalp_points != 0:
            factors.append(f"Scalp directional contribution ({scalp_points:+d})")

        # Clamp final score
        score = max(-100, min(100, int(score)))
        bias_label = MarketBiasEngine._score_to_bias_label(score)

        confidence = min(100, max(15, int(abs(score) + (20 if volume_data.get("spike") else 0))))

        # OTM side suitability (for buying)
        ce_buy_score = max(0, min(100, int(50 + score)))
        pe_buy_score = max(0, min(100, int(50 - score)))

        if score >= 20:
            preferred = "BUY CE OTM"
        elif score <= -20:
            preferred = "BUY PE OTM"
        else:
            preferred = "NO TRADE / WAIT"

        return {
            "market_score": score,
            "market_bias": bias_label,
            "confidence": confidence,
            "ce_otm_buy_score": ce_buy_score,
            "pe_otm_buy_score": pe_buy_score,
            "preferred_otm_side": preferred,
            "factors": factors
        }
