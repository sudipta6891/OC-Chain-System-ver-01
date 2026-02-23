"""
Volume Spike Detection Engine
Designed for breakout confirmation
"""

import pandas as pd


class VolumeEngine:

    @staticmethod
    def detect_volume_spike(
        df: pd.DataFrame,
        atm_strike: float,
        threshold_multiplier: float = 2.0
    ) -> dict:
        """
        Detect volume spike at ATM strike

        threshold_multiplier:
            Current volume > avg_volume * multiplier
        """

        atm_data = df[df["strike_price"] == atm_strike]

        if atm_data.empty:
            return {
                "spike": False,
                "ce_spike": False,
                "pe_spike": False
            }

        ce_data = atm_data[atm_data["option_type"] == "CE"]
        pe_data = atm_data[atm_data["option_type"] == "PE"]

        avg_volume = df["volume"].mean()

        ce_spike = False
        pe_spike = False

        if not ce_data.empty:
            ce_volume = ce_data.iloc[0]["volume"]
            if ce_volume > avg_volume * threshold_multiplier:
                ce_spike = True

        if not pe_data.empty:
            pe_volume = pe_data.iloc[0]["volume"]
            if pe_volume > avg_volume * threshold_multiplier:
                pe_spike = True

        return {
            "spike": ce_spike or pe_spike,
            "ce_spike": ce_spike,
            "pe_spike": pe_spike
        }
