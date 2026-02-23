"""
FYERS Authentication Module

Responsible for:
- Creating authenticated FYERS client
- Validating access token
"""

from fyers_apiv3 import fyersModel
from config.settings import settings


class FyersAuth:
    """
    Handles FYERS API authentication and client creation.
    """

    def __init__(self) -> None:
        self.client_id: str = settings.FYERS_CLIENT_ID
        self.access_token: str = settings.FYERS_ACCESS_TOKEN

    def get_client(self) -> fyersModel.FyersModel:
        """
        Returns authenticated FyersModel instance.
        """

        if not self.access_token:
            raise ValueError(
                "FYERS_ACCESS_TOKEN is missing. "
                "Please generate access token and update .env"
            )

        try:
            fyers = fyersModel.FyersModel(
                client_id=self.client_id,
                token=self.access_token,
                log_path=""
            )

            return fyers

        except Exception as e:
            raise RuntimeError(f"Failed to initialize FYERS client: {e}")
