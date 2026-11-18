import os

# The official MCP servers Deskly can connect to, by id. Each has the name and words shown in
# Connectors, its address, and how it signs in: "oauth" (the user signs in in the browser)
# or "none". "tools" (optional) keeps only those of the server's tools, since every tool's
# description is sent with every question. Adding a server is one entry here.
SERVERS = {
    "github": {
        "name": "GitHub",
        "about": "Your repos, issues and pull requests. Anything that changes GitHub asks you first.",
        "url": "https://api.githubcopilot.com/mcp/",
        "auth": "oauth",
        # GitHub has no read-only repo permission for OAuth Apps; the approval card guards writes
        "scope": "repo read:org read:user notifications",
    },
    "slack": {
        "name": "Slack",
        "about": "Search and read your channels, DMs and files. Sending a message asks you first.",
        "url": "https://mcp.slack.com/mcp",
        "auth": "oauth",
        # Slack only lets "localhost" (not 127.0.0.1) be a desktop app's sign-in address
        "callback_host": "localhost",
        # reading, plus sending messages (each one is approved on its card)
        "scope": " ".join([
            "search:read.public", "search:read.private", "search:read.im", "search:read.mpim",
            "search:read.files", "search:read.users",
            "channels:history", "groups:history", "im:history", "mpim:history",
            "channels:read", "groups:read", "im:read", "mpim:read",
            "users:read", "files:read", "canvases:read", "reactions:read",
            "chat:write",
        ]),
    },
    "notion": {
        "name": "Notion",
        "about": "Search and read your pages and databases. Creating or changing a page asks you first.",
        "url": "https://mcp.notion.com/mcp",
        "auth": "oauth",
        # Notion registers Deskly by itself (no app to set up); "default" is the normal access
        "scope": "default",
        # Notion offers 77 tools worth about 90k tokens, more than half of what the model can
        # hold, so only these are loaded (about 8k)
        "tools": ["notion-search", "notion-fetch", "notion-list-recent-pages", "notion-create-pages", "notion-update-page"],
    },
}

# For trying the MCP support with a local server, e.g. DESKLY_MCP_TEST_URL=http://127.0.0.1:8799/mcp
if os.getenv("DESKLY_MCP_TEST_URL"):
    SERVERS["testmcp"] = {
        "name": "Test server",
        "about": "A local MCP server for trying Deskly's MCP support.",
        "url": os.environ["DESKLY_MCP_TEST_URL"],
        "auth": "none",
    }
