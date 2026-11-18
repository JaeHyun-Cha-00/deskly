import json
import sys
from getpass import getpass

from config import write_private
from connectors.mcp.auth import client_file

# Saves a hand-registered OAuth App's id and secret for one MCP server, without them ever
# going through the chat or git:  uv run python -m connectors.mcp.save_client github
if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "github"
    client_id = input(f"{name} OAuth App Client ID: ").strip()
    # leave the secret empty for an app that uses PKCE instead (Slack)
    client_secret = getpass(f"{name} OAuth App Client secret (hidden; Enter for none): ").strip()
    if not client_id:
        sys.exit("The Client ID is needed.")
    write_private(client_file(name), json.dumps({"client_id": client_id, "client_secret": client_secret}))
    print(f"Saved to {client_file(name)}")
