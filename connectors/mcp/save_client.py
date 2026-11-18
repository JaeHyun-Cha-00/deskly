import json
import os
import sys
from getpass import getpass

from connectors.mcp.auth import TOKENS_DIR, client_file

# Saves a hand-registered OAuth App's id and secret for one MCP server, without them ever
# going through the chat or git:  uv run python -m connectors.mcp.save_client github
if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "github"
    client_id = input(f"{name} OAuth App Client ID: ").strip()
    # leave the secret empty for an app that uses PKCE instead (Slack)
    client_secret = getpass(f"{name} OAuth App Client secret (hidden; Enter for none): ").strip()
    if not client_id:
        sys.exit("The Client ID is needed.")
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(TOKENS_DIR, 0o700)
    client_file(name).write_text(json.dumps({"client_id": client_id, "client_secret": client_secret}))
    os.chmod(client_file(name), 0o600)
    print(f"Saved to {client_file(name)}")
