from connectors.calendar import client as calendar
from connectors.files import client as files
from connectors.gmail import client as gmail
from connectors.mcp.client import apps as mcp_apps

# every app the agent can connect to, by name
APPS = {
    "gmail": gmail,
    "calendar": calendar,
    "files": files,
    # each MCP server in connectors/mcp/servers.py
    **mcp_apps(),
}

def connected():
    return tuple(name for name, client in APPS.items() if client.is_connected())
