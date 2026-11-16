import os

# The official MCP servers Deskly can connect to, by id. Each has the name and words shown in
# Connectors, its address, and how it signs in: "oauth" (the user signs in in the browser)
# or "none". Adding a server is one entry here.
SERVERS = {}

# For trying the MCP support with a local server, e.g. DESKLY_MCP_TEST_URL=http://127.0.0.1:8799/mcp
if os.getenv("DESKLY_MCP_TEST_URL"):
    SERVERS["testmcp"] = {
        "name": "Test server",
        "about": "A local MCP server for trying Deskly's MCP support.",
        "url": os.environ["DESKLY_MCP_TEST_URL"],
        "auth": "none",
    }
