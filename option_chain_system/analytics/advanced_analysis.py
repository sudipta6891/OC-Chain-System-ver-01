"""
Advanced Option Chain Analysis

Provides:
- OI Based Support
- OI Based Resistance
- Max Pain Calculation
"""

import pandas as pd


class AdvancedOptionAnalysis:

    @staticmethod
    def _atm_upside_strikes(
        ce_df: pd.DataFrame,
        pe_df: pd.DataFrame,
        atm: float,
        count: int = 3,
    ) -> list[float]:
        """
        Return ATM and next upside strikes from available chain data.
        """
        strikes = sorted(
            set(pd.to_numeric(ce_df["strike_price"], errors="coerce").dropna().tolist())
            | set(pd.to_numeric(pe_df["strike_price"], errors="coerce").dropna().tolist())
        )
        if not strikes:
            return [float(atm)]

        atm_idx = min(range(len(strikes)), key=lambda idx: abs(strikes[idx] - float(atm)))
        selected = strikes[atm_idx : atm_idx + max(1, int(count))]
        return [float(x) for x in selected]

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

    @staticmethod
    def oi_based_levels_atm_window(
        ce_df: pd.DataFrame,
        pe_df: pd.DataFrame,
        atm: float,
    ) -> tuple[float, float, dict]:
        """
        Determine resistance/support only from ATM, ATM+1, ATM+2 strikes.
        """
        selected_strikes = AdvancedOptionAnalysis._atm_upside_strikes(ce_df, pe_df, atm, count=3)

        ce_window = ce_df[ce_df["strike_price"].isin(selected_strikes)].copy()
        pe_window = pe_df[pe_df["strike_price"].isin(selected_strikes)].copy()

        ce_oi_by_strike = (
            ce_window.groupby("strike_price", as_index=True)["open_interest"].sum().to_dict()
            if not ce_window.empty
            else {}
        )
        pe_oi_by_strike = (
            pe_window.groupby("strike_price", as_index=True)["open_interest"].sum().to_dict()
            if not pe_window.empty
            else {}
        )

        if ce_oi_by_strike:
            resistance = float(max(ce_oi_by_strike.items(), key=lambda x: x[1])[0])
        else:
            resistance = float(selected_strikes[0])

        if pe_oi_by_strike:
            support = float(max(pe_oi_by_strike.items(), key=lambda x: x[1])[0])
        else:
            support = float(selected_strikes[0])

        details = {
            "selected_strikes": [float(x) for x in selected_strikes],
            "ce_oi_by_strike": {float(k): float(v) for k, v in ce_oi_by_strike.items()},
            "pe_oi_by_strike": {float(k): float(v) for k, v in pe_oi_by_strike.items()},
            "resistance": resistance,
            "support": support,
        }
        return resistance, support, details

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
