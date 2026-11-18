import threading
from collections import defaultdict
from functools import cache

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import CREDENTIALS_FILE, token_file, write_private

# after changing an app's scopes, disconnect it so the next use signs in again
SCOPES = {
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly"],
    "calendar": [
        "https://www.googleapis.com/auth/calendar.readonly",
        # adding events (each one approved by the user first)
        "https://www.googleapis.com/auth/calendar.events",
    ],
}

# one sign-in at a time, so two tools starting together don't open two sign-in pages
SIGN_IN = threading.Lock()

def get_credentials(app):
    with SIGN_IN:
        return load_credentials(app)

@cache
def load_credentials(app):
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
        write_private(file, creds.to_json())

    return creds

def is_signed_in(app):
    return token_file(app).exists()

def broken_sign_ins():
    # After Google refused a saved sign-in: the Google apps whose sign-in no longer works.
    # Other apps (files, MCP servers) are never in it. A network problem is not a broken
    # sign-in, so it doesn't count.
    broken = []
    for app in SCOPES:
        if not is_signed_in(app):
            continue
        try:
            Credentials.from_authorized_user_file(str(token_file(app)), SCOPES[app]).refresh(Request())
        except RefreshError:
            broken.append(app)
        except Exception:
            pass
    return broken

# Google's HTTP library isn't safe to share between threads, and the agent runs tools in
# parallel threads, so each thread builds its own service. Signing out raises the app's
# generation, which makes every thread build a new one.
THREADS = threading.local()
GENERATION = defaultdict(int)

def service(app, api, version):
    built = THREADS.__dict__.setdefault("services", {})
    key = (app, GENERATION[app])
    if key not in built:
        built[key] = build(api, version, credentials=get_credentials(app), cache_discovery=False)
    return built[key]

def forget_credentials(app):
    token_file(app).unlink(missing_ok=True)
    load_credentials.cache_clear()
    GENERATION[app] += 1
