import unittest
import os
import sys

sys.path.append(os.path.dirname(__file__))
try:
    from config.settings import settings
except Exception:
    settings = None


@unittest.skipIf(settings is None, "settings unavailable or env not configured")
class TestSettings(unittest.TestCase):
    def test_has_required_runtime_fields(self):
        self.assertTrue(hasattr(settings, "TIMEZONE"))
        self.assertTrue(hasattr(settings, "TEST_MODE"))
        self.assertTrue(hasattr(settings, "OPTION_CHAIN_STRIKE_COUNT"))
        self.assertGreaterEqual(settings.OPTION_CHAIN_STRIKE_COUNT, 20)


if __name__ == "__main__":
    unittest.main()
