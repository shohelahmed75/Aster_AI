"""
auth.py — OAuth 2.0 authentication for the YouTube Data API v3.

Handles the full auth flow:
  1. Load cached credentials from token.json
  2. Refresh expired credentials
  3. If no valid credentials exist, launch browser-based OAuth consent flow
  4. Build and return an authenticated YouTube API service object
"""

import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from aster.core.config import CLIENT_SECRET_FILE, TOKEN_FILE, SCOPES

logger = logging.getLogger("aster")


def get_authenticated_service():
    """
    Returns an authenticated YouTube Data API v3 service object.

    On first run, opens a browser window for Google sign-in.
    Subsequent runs use the cached token.json file.
    """
    credentials = _load_or_refresh_token()

    # Build the YouTube API service
    youtube = build("youtube", "v3", credentials=credentials)
    return youtube


def _load_or_refresh_token():
    """
    Load credentials from token.json, refresh if expired,
    or start a new OAuth flow if no valid token exists.
    """
    credentials = None

    # Step 1: Try to load existing credentials
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Step 2: Refresh or re-authenticate
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("🔄 Refreshing expired credentials...")
            credentials.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"\n❌ '{CLIENT_SECRET_FILE}' not found!\n"
                    f"   Please download your OAuth 2.0 client credentials from\n"
                    f"   Google Cloud Console and save them as 'client_secret.json'\n"
                    f"   in the project root directory.\n"
                )

            logger.info("🔐 Starting OAuth 2.0 authentication flow...")
            logger.info("   A browser window will open for Google sign-in.\n")

            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            credentials = flow.run_local_server(port=0)

        # Step 3: Save credentials for future runs
        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(credentials.to_json())
        logger.info(f"✅ Credentials saved to '{TOKEN_FILE}'\n")

    return credentials
