import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.append(os.path.dirname(__file__))
try:
    import data_layer.fyers_auth as fyers_auth_module
except Exception:
    fyers_auth_module = None


@unittest.skipIf(fyers_auth_module is None, "fyers auth dependencies unavailable")
class TestFyersAuth(unittest.TestCase):
    @patch.object(fyers_auth_module, "fyersModel")
    def test_get_client_builds_fyers_model(self, mock_fyers_model):
        mock_fyers_model.FyersModel = MagicMock(return_value="mock_client")

        with patch.object(fyers_auth_module.settings, "FYERS_CLIENT_ID", "abc"), patch.object(
            fyers_auth_module.settings, "FYERS_ACCESS_TOKEN", "token123"
        ):
            auth = fyers_auth_module.FyersAuth()
            client = auth.get_client()

        self.assertEqual(client, "mock_client")
        mock_fyers_model.FyersModel.assert_called_once()


if __name__ == "__main__":
    unittest.main()
