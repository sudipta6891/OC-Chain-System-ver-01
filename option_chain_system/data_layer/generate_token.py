"""
Generate FYERS Access Token

Run this script manually to generate access token.
After generation, paste token into .env file.
"""

from fyers_apiv3 import fyersModel
from config.settings import settings


def generate_auth_code() -> None:
    """
    Step 1: Generate login URL
    """

    session = fyersModel.SessionModel(
        client_id=settings.FYERS_CLIENT_ID,
        secret_key=settings.FYERS_SECRET_KEY,
        redirect_uri=settings.FYERS_REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )

    auth_url = session.generate_authcode()

    print("\nLogin URL:\n")
    print(auth_url)
    print("\nOpen this URL in browser and login.")
    print("After login, copy the 'auth_code' from redirected URL.\n")


def generate_access_token(auth_code: str) -> None:
    """
    Step 2: Generate access token using auth code
    """

    session = fyersModel.SessionModel(
        client_id=settings.FYERS_CLIENT_ID,
        secret_key=settings.FYERS_SECRET_KEY,
        redirect_uri=settings.FYERS_REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )

    session.set_token(auth_code)

    response = session.generate_token()

    if response.get("s") != "ok":
        raise Exception(f"Token generation failed: {response}")

    access_token = response["access_token"]

    print("\nAccess Token Generated Successfully:\n")
    print(access_token)
    print("\nCopy this token and paste into .env as FYERS_ACCESS_TOKEN\n")


if __name__ == "__main__":

    print("STEP 1: Generate Login URL\n")
    generate_auth_code()

    auth_code_input = input("Enter auth_code from redirected URL: ")

    print("\nSTEP 2: Generating Access Token...\n")
    generate_access_token(auth_code_input)
