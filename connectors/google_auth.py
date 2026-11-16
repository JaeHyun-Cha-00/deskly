import os
from functools import cache

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import CREDENTIALS_FILE, token_file

# after changing an app's scopes, disconnect it so the next use signs in again
SCOPES = {
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly"],
    "calendar": ["https://www.googleapis.com/auth/calendar.readonly"],
}

@cache
def get_credentials(app):
    file = token_file(app)
    creds = None
    if file.exists():
        creds = Credentials.from_authorized_user_file(str(file), SCOPES[app])

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES[app])
            # give up after 3 minutes if the sign-in window is closed
            creds = flow.run_local_server(port=0, timeout_seconds=180)
        file.write_text(creds.to_json())
        os.chmod(file, 0o600)

    return creds

def is_signed_in(app):
    return token_file(app).exists()

def forget_credentials(app):
    token_file(app).unlink(missing_ok=True)
    get_credentials.cache_clear()
