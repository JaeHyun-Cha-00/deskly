import os
from functools import cache

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import CREDENTIALS_FILE, TOKEN_FILE

# after changing SCOPES, disconnect Gmail so the next use signs in again
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

@cache
def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            # give up after 3 minutes if the sign-in window is closed
            creds = flow.run_local_server(port=0, timeout_seconds=180)
        TOKEN_FILE.write_text(creds.to_json())
        os.chmod(TOKEN_FILE, 0o600)

    return creds

def forget_credentials():
    TOKEN_FILE.unlink(missing_ok=True)
    get_credentials.cache_clear()
