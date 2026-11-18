import base64
import re

from connectors.google_auth import forget_credentials, get_credentials, is_signed_in, service

# how it shows in Connectors
NAME = "Gmail"
ABOUT = "Search and read your mail. I can't send, delete or change anything."
GROUP = "Google"

MAX_BODY_CHARS = 4000

def get_service():
    # this thread's own connection to Google (see google_auth.service)
    return service("gmail", "gmail", "v1")

def header(message, name):
    for h in message["payload"].get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""

def decode(data):
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

def body_text(payload):
    plain, html = "", ""
    parts = [payload]
    while parts:
        part = parts.pop()
        parts += part.get("parts", [])
        data = part.get("body", {}).get("data")
        if data and part.get("mimeType") == "text/plain" and not plain:
            plain = decode(data)
        if data and part.get("mimeType") == "text/html" and not html:
            html = re.sub(r"<[^>]+>", " ", decode(data))

    text = re.sub(r"\s+", " ", plain or html).strip()
    return text[:MAX_BODY_CHARS]

def connect():
    # opens Google's sign-in the first time; later it reuses the saved sign-in
    get_credentials("gmail")

def is_connected():
    return is_signed_in("gmail")

def sign_out():
    forget_credentials("gmail")
