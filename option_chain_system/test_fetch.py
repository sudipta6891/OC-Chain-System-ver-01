import unittest
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(__file__))
try:
    import pandas as pd
    from analytics.data_quality_engine import DataQualityEngine
except Exception:
    pd = None
    DataQualityEngine = None


@unittest.skipIf(pd is None or DataQualityEngine is None, "pandas or analytics dependencies unavailable")
class TestDataQualityEngine(unittest.TestCase):
    def test_detects_basic_quality_flags(self):
        now = datetime.now()
        df = pd.DataFrame(
            [
                {"strike_price": 50000, "option_type": "CE", "open_interest": 1000, "oi_change": 10, "volume": 250, "ltp": 120},
                {"strike_price": 50000, "option_type": "PE", "open_interest": 1000, "oi_change": -12, "volume": 240, "ltp": 110},
                {"strike_price": 50100, "option_type": "CE", "open_interest": 900, "oi_change": 5, "volume": 180, "ltp": 95},
                {"strike_price": 50100, "option_type": "PE", "open_interest": 900, "oi_change": 4, "volume": 170, "ltp": 97},
            ]
        )
        result = DataQualityEngine.assess(
            symbol="NSE:NIFTYBANK-INDEX",
            df=df,
            spot=50050,
            snapshot_time=now,
        )
        self.assertTrue(result.is_usable)
        self.assertFalse(result.stale_data)


if __name__ == "__main__":
    unittest.main()
