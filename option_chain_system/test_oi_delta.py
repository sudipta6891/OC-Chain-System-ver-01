import unittest
import os
import sys

sys.path.append(os.path.dirname(__file__))
try:
    from analytics.intraday_oi_engine import IntradayOIDeltaEngine
except Exception:
    IntradayOIDeltaEngine = None


@unittest.skipIf(IntradayOIDeltaEngine is None, "oi delta dependencies unavailable")
class TestIntradayOIDeltaEngine(unittest.TestCase):
    def test_default_response_shape(self):
        response = IntradayOIDeltaEngine._default_response("No Data")  # noqa: SLF001
        self.assertIn("ce_delta", response)
        self.assertIn("pe_delta", response)
        self.assertEqual(response["classification"], "No Data")
        self.assertEqual(response["bullish_probability"], 50)
        self.assertEqual(response["bearish_probability"], 50)


if __name__ == "__main__":
    unittest.main()
