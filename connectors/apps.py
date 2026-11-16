from connectors.calendar import client as calendar
from connectors.gmail import client as gmail

# every app the agent can connect to, by name
APPS = {
    "gmail": gmail,
    "calendar": calendar,
}

def connected():
    return tuple(name for name, client in APPS.items() if client.is_connected())
