"""
Basic Option Chain Analysis

Provides:
- ATM Detection
- CE / PE Separation
- Total OI
- PCR Calculation
"""

import pandas as pd


class BasicOptionAnalysis:

    @staticmethod
    def detect_atm_strike(
        df: pd.DataFrame,
        spot_price: float
    ) -> float:
        """
        Detect nearest ATM strike
        """

        strikes = df["strike_price"].unique()

        atm_strike = min(
            strikes,
            key=lambda x: abs(x - spot_price)
        )

        return float(atm_strike)

    # -----------------------------------
    @staticmethod
    def split_ce_pe(
        df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Separate CE and PE
        """

        ce_df = df[df["option_type"] == "CE"].copy()
        pe_df = df[df["option_type"] == "PE"].copy()

        return ce_df, pe_df

    # -----------------------------------
    @staticmethod
    def calculate_total_oi(
        ce_df: pd.DataFrame,
        pe_df: pd.DataFrame
    ) -> tuple[float, float]:

        total_ce_oi = ce_df["open_interest"].sum()
        total_pe_oi = pe_df["open_interest"].sum()

        return float(total_ce_oi), float(total_pe_oi)

    # -----------------------------------
    @staticmethod
    def calculate_pcr(
        total_pe_oi: float,
        total_ce_oi: float
    ) -> float:

        if total_ce_oi == 0:
            return 0.0

        return round(total_pe_oi / total_ce_oi, 4)
