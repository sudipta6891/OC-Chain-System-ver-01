"""
Application Configuration Loader
Loads all environment variables securely.
"""

from dotenv import load_dotenv
import os
# Load .env file
load_dotenv()

class Settings:
    """
    Central configuration class.
    """

    def __init__(self) -> None:
        self.FYERS_CLIENT_ID: str = os.getenv("FYERS_CLIENT_ID", "")
        self.FYERS_SECRET_KEY: str = os.getenv("FYERS_SECRET_KEY", "")
        self.FYERS_REDIRECT_URI: str = os.getenv("FYERS_REDIRECT_URI", "")
        self.FYERS_ACCESS_TOKEN: str = os.getenv("FYERS_ACCESS_TOKEN", "")
        self.TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
        self.TEST_MODE: bool = os.getenv("TEST_MODE", "False") == "True"
        self.DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", 7))
        self.OPTION_CHAIN_STRIKE_COUNT: int = int(os.getenv("OPTION_CHAIN_STRIKE_COUNT", 40))
        self.ENABLE_ALL_ENHANCEMENTS: bool = os.getenv("ENABLE_ALL_ENHANCEMENTS", "False") == "True"
        self.ENABLE_GUARDRAILS: bool = os.getenv("ENABLE_GUARDRAILS", "True") == "True"
        self.ENABLE_REGIME_V2: bool = os.getenv("ENABLE_REGIME_V2", "False") == "True"
        self.ENABLE_TIMING_V2: bool = os.getenv("ENABLE_TIMING_V2", "False") == "True"
        self.ENABLE_DYNAMIC_OTM: bool = os.getenv("ENABLE_DYNAMIC_OTM", "False") == "True"
        self.ENABLE_OUTCOME_TRACKING: bool = os.getenv("ENABLE_OUTCOME_TRACKING", "False") == "True"
        self.ENABLE_CALIBRATION: bool = os.getenv("ENABLE_CALIBRATION", "False") == "True"
        self.CALIBRATION_MIN_SAMPLES: int = int(os.getenv("CALIBRATION_MIN_SAMPLES", 30))

        if self.ENABLE_ALL_ENHANCEMENTS:
            self.ENABLE_GUARDRAILS = True
            self.ENABLE_REGIME_V2 = True
            self.ENABLE_TIMING_V2 = True
            self.ENABLE_DYNAMIC_OTM = True
            self.ENABLE_OUTCOME_TRACKING = True
            self.ENABLE_CALIBRATION = True

        # Database Config
        self.DB_NAME: str = os.getenv("DB_NAME", "")
        self.DB_USER: str = os.getenv("DB_USER", "")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT: str = os.getenv("DB_PORT", "5432")

        # Email Config
        self.EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
        self.EMAIL_APP_PASSWORD: str = os.getenv("EMAIL_APP_PASSWORD", "")
        self.EMAIL_RECIPIENTS: str = os.getenv("EMAIL_RECIPIENTS", "")



        self._validate()

    def _validate(self) -> None:
        """
        Basic validation to ensure required variables exist.
        """
        if not self.FYERS_CLIENT_ID:
            raise ValueError("FYERS_CLIENT_ID missing in .env")

        if not self.FYERS_SECRET_KEY:
            raise ValueError("FYERS_SECRET_KEY missing in .env")

        if not self.FYERS_REDIRECT_URI:
            raise ValueError("FYERS_REDIRECT_URI missing in .env")


# Global settings instance
settings = Settings()
