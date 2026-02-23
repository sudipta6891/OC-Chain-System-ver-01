"""
Far OTM Strike Selector
Selects OTM strikes based on % distance
"""

import pandas as pd


class OTMSelector:

    @staticmethod
    def select_far_otm(
        df: pd.DataFrame,
        spot: float,
        direction: str,
        distance_percent: float = 2.0
    ) -> float:
        """
        Select far OTM strike

        direction: "CE" or "PE"
        distance_percent: % away from spot
        """

        target_price = None

        if direction == "CE":
            target_price = spot * (1 + distance_percent / 100)
            eligible = df[
                (df["option_type"] == "CE") &
                (df["strike_price"] >= target_price)
            ]

        elif direction == "PE":
            target_price = spot * (1 - distance_percent / 100)
            eligible = df[
                (df["option_type"] == "PE") &
                (df["strike_price"] <= target_price)
            ]

        else:
            return None

        if eligible.empty:
            return None

        # Select nearest far OTM strike
        strike = eligible.iloc[0]["strike_price"]

        return float(strike)
