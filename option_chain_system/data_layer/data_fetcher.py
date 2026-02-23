"""
Data Fetcher Module (Corrected for FYERS V3)

Responsible for:
- Fetching Spot Price
- Fetching Option Chain
- Cleaning & Structuring Data
"""

from typing import Dict, Any
import pandas as pd
from datetime import datetime
import pytz

from fyers_apiv3 import fyersModel
from data_layer.fyers_auth import FyersAuth
from config.settings import settings


class OptionChainFetcher:

    def __init__(self) -> None:
        auth = FyersAuth()
        self.fyers: fyersModel.FyersModel = auth.get_client()
        self.timezone = pytz.timezone(settings.TIMEZONE)

    # -----------------------------------
    # Spot Price
    # -----------------------------------
    def fetch_spot_price(self, symbol: str) -> float:
        """
        Fetch current spot price of index
        Robust version
        """

        response: Dict[str, Any] = self.fyers.quotes(
            {"symbols": symbol}
        )

        if response.get("s") != "ok":
            raise ValueError(f"Invalid response: {response}")

        try:
            quote_data = response["d"][0]["v"]

            # Try standard field
            if "lp" in quote_data:
                return float(quote_data["lp"])

            # Fallback option
            if "last_price" in quote_data:
                return float(quote_data["last_price"])

            # If still missing, print structure
            print("Unexpected quote structure:", response)
            raise KeyError("Spot price field not found")

        except Exception as e:
            raise RuntimeError(f"Spot price fetch failed: {e}")


    # -----------------------------------
    # Option Chain
    # -----------------------------------
    def fetch_option_chain(self, symbol: str) -> pd.DataFrame:

        data = {
            "symbol": symbol,
            "strikecount": settings.OPTION_CHAIN_STRIKE_COUNT,
            "timestamp": ""
        }

        response = self.fyers.optionchain(data=data)

        if response.get("s") != "ok":

            if response.get("code") == -470:
                print(f"No expiry contracts available for {symbol}")
                return pd.DataFrame()

            raise ValueError(f"Invalid API response: {response}")

        option_data = response["data"]["optionsChain"]

        if not option_data:
            raise ValueError("No option chain data received")

        df = pd.DataFrame(option_data)

        return self._clean_dataframe(df, symbol)

    # -----------------------------------
    # Data Cleaning
    # -----------------------------------
    def _clean_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> pd.DataFrame:

        required_columns = [
            "strike_price",
            "option_type",
            "oi",
            "oich",
            "volume",
            "ltp"
        ]

        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        df = df.rename(columns={
            "oi": "open_interest",
            "oich": "oi_change"
        })

        # Normalize dtypes early for robust analytics
        for col in ["strike_price", "open_interest", "oi_change", "volume", "ltp"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["strike_price", "option_type", "open_interest", "volume", "ltp"])

        # Remove underlying row (strike_price = -1)
        df = df[df["strike_price"] != -1]

        df["symbol"] = symbol
        df["snapshot_time"] = datetime.now(self.timezone)

        core_columns = [
            "symbol",
            "strike_price",
            "option_type",
            "open_interest",
            "oi_change",
            "volume",
            "ltp",
            "snapshot_time",
        ]

        optional_columns = []
        for col in ["iv", "implied_volatility", "impliedVolatility", "expiry", "expiry_date", "expiryDate", "exd"]:
            if col in df.columns:
                optional_columns.append(col)

        df = df[core_columns + optional_columns]

        df = df.sort_values(["strike_price", "option_type"]).reset_index(drop=True)
        return df
