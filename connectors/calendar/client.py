from functools import cache

from googleapiclient.discovery import build

from connectors.google_auth import forget_credentials, get_credentials, is_signed_in

@cache
def get_service():
    return build("calendar", "v3", credentials=get_credentials("calendar"))

def is_connected():
    return is_signed_in("calendar")

def sign_out():
    forget_credentials("calendar")
    get_service.cache_clear()
