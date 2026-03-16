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
        baseline_ce_oi_by_strike: dict | None = None,
        baseline_pe_oi_by_strike: dict | None = None,
    ) -> tuple[float, float, dict]:
        """
        Determine resistance/support only from ATM, ATM+1, ATM+2 strikes.
        """
        strikes = sorted(
            set(pd.to_numeric(ce_df["strike_price"], errors="coerce").dropna().tolist())
            | set(pd.to_numeric(pe_df["strike_price"], errors="coerce").dropna().tolist())
        )
        selected_strikes = AdvancedOptionAnalysis._atm_upside_strikes(ce_df, pe_df, atm, count=3)
        atm_ref_strike = selected_strikes[0] if selected_strikes else float(atm)

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
        baseline_ce_oi_by_strike = baseline_ce_oi_by_strike or {}
        baseline_pe_oi_by_strike = baseline_pe_oi_by_strike or {}
        if baseline_ce_oi_by_strike or baseline_pe_oi_by_strike:
            ce_oi_change_by_strike = {}
            pe_oi_change_by_strike = {}
            ce_oi_change_all_by_strike = {}
            pe_oi_change_all_by_strike = {}
            for strike in selected_strikes:
                current_ce_oi = float(ce_oi_by_strike.get(strike, 0.0))
                current_pe_oi = float(pe_oi_by_strike.get(strike, 0.0))
                base_ce_oi = float(baseline_ce_oi_by_strike.get(strike, 0.0))
                base_pe_oi = float(baseline_pe_oi_by_strike.get(strike, 0.0))
                ce_oi_change_by_strike[float(strike)] = current_ce_oi - base_ce_oi
                pe_oi_change_by_strike[float(strike)] = current_pe_oi - base_pe_oi
            for strike in strikes:
                current_ce_oi_all = float(
                    pd.to_numeric(
                        ce_df.loc[ce_df["strike_price"] == strike, "open_interest"],
                        errors="coerce",
                    ).fillna(0.0).sum()
                )
                current_pe_oi_all = float(
                    pd.to_numeric(
                        pe_df.loc[pe_df["strike_price"] == strike, "open_interest"],
                        errors="coerce",
                    ).fillna(0.0).sum()
                )
                base_ce_oi_all = float(baseline_ce_oi_by_strike.get(float(strike), 0.0))
                base_pe_oi_all = float(baseline_pe_oi_by_strike.get(float(strike), 0.0))
                ce_oi_change_all_by_strike[float(strike)] = current_ce_oi_all - base_ce_oi_all
                pe_oi_change_all_by_strike[float(strike)] = current_pe_oi_all - base_pe_oi_all
        else:
            ce_oi_change_by_strike = (
                ce_window.groupby("strike_price", as_index=True)["oi_change"].sum().to_dict()
                if (not ce_window.empty and "oi_change" in ce_window.columns)
                else {}
            )
            pe_oi_change_by_strike = (
                pe_window.groupby("strike_price", as_index=True)["oi_change"].sum().to_dict()
                if (not pe_window.empty and "oi_change" in pe_window.columns)
                else {}
            )
            ce_oi_change_all_by_strike = (
                ce_df.groupby("strike_price", as_index=True)["oi_change"].sum().to_dict()
                if (not ce_df.empty and "oi_change" in ce_df.columns)
                else {}
            )
            pe_oi_change_all_by_strike = (
                pe_df.groupby("strike_price", as_index=True)["oi_change"].sum().to_dict()
                if (not pe_df.empty and "oi_change" in pe_df.columns)
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

        call_sum = float(sum(float(v) for v in ce_oi_change_by_strike.values()))
        put_sum = float(sum(float(v) for v in pe_oi_change_by_strike.values()))
        if put_sum > call_sum:
            pressure_direction = "Bullish"
        elif call_sum > put_sum:
            pressure_direction = "Bearish"
        else:
            pressure_direction = "Neutral"

        diffs = [float(b - a) for a, b in zip(strikes, strikes[1:]) if float(b - a) > 0]
        strike_step = min(diffs) if diffs else 0.0
        atm_idx = min(range(len(strikes)), key=lambda idx: abs(strikes[idx] - float(atm_ref_strike))) if strikes else 0
        sp_plus_4_strike = float(strikes[atm_idx + 4]) if strikes and (atm_idx + 4) < len(strikes) else None
        sp_minus_2_strike = float(strikes[atm_idx - 2]) if strikes and (atm_idx - 2) >= 0 else None

        p4 = float(pe_oi_change_all_by_strike.get(sp_plus_4_strike, 0.0)) if sp_plus_4_strike is not None else 0.0
        p5 = float(ce_oi_change_all_by_strike.get(sp_plus_4_strike, 0.0)) if sp_plus_4_strike is not None else 0.0
        p6 = float(ce_oi_change_all_by_strike.get(sp_minus_2_strike, 0.0)) if sp_minus_2_strike is not None else 0.0
        p7 = float(pe_oi_change_all_by_strike.get(sp_minus_2_strike, 0.0)) if sp_minus_2_strike is not None else 0.0
        call_itm = float(p4 / p5) if p5 != 0 else None
        put_itm = float(p6 / p7) if p7 != 0 else None

        details = {
            "selected_strikes": [float(x) for x in selected_strikes],
            "ce_oi_by_strike": {float(k): float(v) for k, v in ce_oi_by_strike.items()},
            "pe_oi_by_strike": {float(k): float(v) for k, v in pe_oi_by_strike.items()},
            "ce_oi_change_by_strike": {float(k): float(v) for k, v in ce_oi_change_by_strike.items()},
            "pe_oi_change_by_strike": {float(k): float(v) for k, v in pe_oi_change_by_strike.items()},
            "ce_oi_change_all_by_strike": {float(k): float(v) for k, v in ce_oi_change_all_by_strike.items()},
            "pe_oi_change_all_by_strike": {float(k): float(v) for k, v in pe_oi_change_all_by_strike.items()},
            "call_pressure_sum": call_sum,
            "put_pressure_sum": put_sum,
            "pressure_direction": pressure_direction,
            "atm_reference_strike": float(atm_ref_strike),
            "strike_step": float(strike_step),
            "sp_plus_4_strike": sp_plus_4_strike,
            "sp_minus_2_strike": sp_minus_2_strike,
            "p4": p4,
            "p5": p5,
            "p6": p6,
            "p7": p7,
            "call_itm": call_itm,
            "put_itm": put_itm,
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
