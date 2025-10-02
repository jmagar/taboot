#!/usr/bin/env python3
"""Google OAuth2 authentication helper for Gmail API.

Run this script to obtain a refresh token for Gmail access.
Requires: pip install google-auth-oauthlib
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main() -> None:
    """Run OAuth flow and display refresh token."""
    # Try loading from .env first
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

    # Fallback to prompting if not in .env
    if not client_id:
        client_id = input("Enter your Google Client ID: ").strip()
    else:
        print(f"Using GOOGLE_CLIENT_ID from .env")

    if not client_secret:
        client_secret = input("Enter your Google Client Secret: ").strip()
    else:
        print(f"Using GOOGLE_CLIENT_SECRET from .env")

    if not client_id or not client_secret:
        raise ValueError("Client ID and Client Secret are required")

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        SCOPES,
    )

    print("\nStarting OAuth flow...")
    print("A browser window will open for authentication.")
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("SUCCESS! Add these to your .env file:")
    print("=" * 60)
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
