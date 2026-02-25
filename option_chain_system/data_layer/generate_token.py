"""
Generate FYERS Access Token

Run this script manually to generate access token.
After generation, paste token into .env file.
"""

import argparse
import sys

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


def _read_auth_code_interactive() -> str:
    try:
        auth_code_input = input("Enter auth_code from redirected URL: ")
    except EOFError as exc:
        raise RuntimeError(
            "No interactive stdin available for auth_code input. "
            "Run with --auth-code '<value>' instead."
        ) from exc
    return auth_code_input.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FYERS access token helper")
    parser.add_argument(
        "--auth-code",
        dest="auth_code",
        help="Auth code copied from FYERS redirected URL",
    )
    parser.add_argument(
        "--print-auth-url",
        action="store_true",
        help="Only print login URL and exit",
    )
    args = parser.parse_args()

    print("STEP 1: Generate Login URL\n")
    generate_auth_code()

    if args.print_auth_url:
        sys.exit(0)

    auth_code_input = (args.auth_code or "").strip()
    if not auth_code_input:
        auth_code_input = _read_auth_code_interactive()
    if not auth_code_input:
        raise ValueError("auth_code is empty. Copy the value from redirected URL and retry.")

    print("\nSTEP 2: Generating Access Token...\n")
    generate_access_token(auth_code_input)
