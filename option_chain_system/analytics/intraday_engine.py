"""
Intraday Outlook Engine
Generates short-term directional projections
"""

class IntradayEngine:

    @staticmethod
    def generate_outlook(
        spot: float,
        resistance: float,
        support: float,
        prob_data: dict,
        breakout_signal: str
    ) -> dict:

        bias = prob_data["bias"]
        upside = prob_data["upside_probability"]
        downside = prob_data["downside_probability"]

        # Default Outlook
        outlook_15 = "Range Movement Expected"
        outlook_30 = "Consolidation Likely"
        outlook_60 = "Neutral Structure"

        # Bullish Bias
        if bias == "Bullish":

            if breakout_signal == "Bullish Breakout":
                outlook_15 = "Momentum Continuation Likely"
                outlook_30 = "Upside Expansion Towards Higher Strikes"
                outlook_60 = "Sustained Buying Pressure Possible"

            else:
                outlook_15 = "Minor Pullback Possible"
                outlook_30 = "Upside Retest Towards Resistance"
                outlook_60 = "Gradual Strength Building"

        # Bearish Bias
        elif bias == "Bearish":

            if breakout_signal == "Bearish Breakdown":
                outlook_15 = "Immediate Selling Pressure"
                outlook_30 = "Downside Expansion Towards Lower Strikes"
                outlook_60 = "Sustained Pressure If Support Breaks"

            else:
                outlook_15 = "Minor Pullback Possible"
                outlook_30 = "Downside Test Towards Support"
                outlook_60 = "Sustained Pressure If Resistance Holds"

        # Neutral Bias
        else:
            outlook_15 = "Whipsaw Possible"
            outlook_30 = "Range Bound Between Key Levels"
            outlook_60 = "Wait For Breakout Confirmation"

        return {
            "next_15": outlook_15,
            "next_30": outlook_30,
            "next_60": outlook_60
        }
