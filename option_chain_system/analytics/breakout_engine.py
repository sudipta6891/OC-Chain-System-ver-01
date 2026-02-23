"""
Breakout & Expansion Engine
Designed for Far OTM Buying Strategy
"""

import pandas as pd


class BreakoutEngine:

    @staticmethod
    def detect_breakout(
        spot: float,
        resistance: float,
        support: float
    ) -> str:

        if spot > resistance:
            return "Bullish Breakout"

        if spot < support:
            return "Bearish Breakdown"

        return "No Breakout"

    # -----------------------------------

    @staticmethod
    def detect_short_covering(
        ce_df: pd.DataFrame,
        pe_df: pd.DataFrame
    ) -> str:

        ce_change = ce_df["oi_change"].sum()
        pe_change = pe_df["oi_change"].sum()

        # CE OI decreasing strongly
        if ce_change < 0:
            return "Bullish Short Covering (Calls)"

        # PE OI decreasing strongly
        if pe_change < 0:
            return "Bearish Short Covering (Puts)"

        return "No Short Covering"
