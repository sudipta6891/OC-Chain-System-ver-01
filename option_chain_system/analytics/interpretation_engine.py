"""
Institutional Interpretation Engine

Detects:
- Call Writing
- Put Writing
- Long Build Up
- Short Covering
- Trap Setup
"""

import pandas as pd


class InterpretationEngine:

    @staticmethod
    def detect_writing(
        ce_df: pd.DataFrame,
        pe_df: pd.DataFrame
    ) -> str:

        ce_oi_change = ce_df["oi_change"].sum()
        pe_oi_change = pe_df["oi_change"].sum()

        if ce_oi_change > 0 and pe_oi_change < 0:
            return "Call Writing Dominant (Bearish Bias)"

        if pe_oi_change > 0 and ce_oi_change < 0:
            return "Put Writing Dominant (Bullish Bias)"

        if ce_oi_change > 0 and pe_oi_change > 0:
            return "Both Side Writing (Range Formation)"

        return "Unclear Structure"

    # -----------------------------------
    @staticmethod
    def detect_trap(
        spot: float,
        resistance: float,
        support: float
    ) -> str:

        if spot > resistance:
            return "Possible Call Trap (Above Resistance)"

        if spot < support:
            return "Possible Put Trap (Below Support)"

        return "No Trap Detected"
