"""
Advanced Option Chain Analysis

Provides:
- OI Based Support
- OI Based Resistance
- Max Pain Calculation
"""

import pandas as pd


class AdvancedOptionAnalysis:

    # -----------------------------------
    @staticmethod
    def oi_based_levels(
        ce_df: pd.DataFrame,
        pe_df: pd.DataFrame
    ) -> tuple[float, float]:
        """
        Determine resistance (max CE OI)
        and support (max PE OI)
        """

        resistance = ce_df.loc[
            ce_df["open_interest"].idxmax(),
            "strike_price"
        ]

        support = pe_df.loc[
            pe_df["open_interest"].idxmax(),
            "strike_price"
        ]

        return float(resistance), float(support)

    # -----------------------------------
    @staticmethod
    def calculate_max_pain(
        df: pd.DataFrame
    ) -> float:
        """
        Calculate Max Pain level
        """

        strikes = sorted(df["strike_price"].unique())
        max_pain_data = []

        for strike in strikes:

            total_loss = 0

            for _, row in df.iterrows():

                if row["option_type"] == "CE":
                    intrinsic = max(0, strike - row["strike_price"])
                else:
                    intrinsic = max(0, row["strike_price"] - strike)

                total_loss += intrinsic * row["open_interest"]

            max_pain_data.append((strike, total_loss))

        # Strike with minimum total loss
        max_pain_strike = min(
            max_pain_data,
            key=lambda x: x[1]
        )[0]

        return float(max_pain_strike)
