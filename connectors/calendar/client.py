
from connectors.google_auth import forget_credentials, get_credentials, is_signed_in, service

# how it shows in Connectors
NAME = "Google Calendar"
ABOUT = "See your events. Adding an event asks you first."
GROUP = "Google"

def get_service():
    # this thread's own connection to Google (see google_auth.service)
    return service("calendar", "calendar", "v3")

def connect():
    # opens Google's sign-in the first time; later it reuses the saved sign-in
    get_credentials("calendar")

def is_connected():
    return is_signed_in("calendar")

def sign_out():
    forget_credentials("calendar")
