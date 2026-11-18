from functools import cache

from googleapiclient.discovery import build

from connectors.google_auth import forget_credentials, get_credentials, is_signed_in

# how it shows in Connectors
NAME = "Google Calendar"
ABOUT = "See your events. Adding an event asks you first."
GROUP = "Google"

@cache
def get_service():
    return build("calendar", "v3", credentials=get_credentials("calendar"))

def connect():
    # opens Google's sign-in the first time; later it reuses the saved sign-in
    get_credentials("calendar")

def is_connected():
    return is_signed_in("calendar")

def sign_out():
    forget_credentials("calendar")
    get_service.cache_clear()
