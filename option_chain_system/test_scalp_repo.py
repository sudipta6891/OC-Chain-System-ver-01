import unittest
import os
import sys

sys.path.append(os.path.dirname(__file__))
from analytics.scalp_engine import OTMScalpEngine


class TestScalpEngine(unittest.TestCase):
    def test_returns_buy_when_signals_align(self):
        result = OTMScalpEngine.generate_signal(
            breakout_signal="Bullish Breakout",
            covering_signal="Bullish Short Covering (Calls)",
            volume_data={"spike": True, "ce_spike": True, "pe_spike": False},
            prob_data={"upside_probability": 72, "downside_probability": 28},
        )
        self.assertIn(result["signal"], {"BUY OTM", "STRONG BUY OTM"})
        self.assertGreater(result["score"], 0)


if __name__ == "__main__":
    unittest.main()
