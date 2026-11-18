import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

from connectors import event_loop
from connectors.mcp import auth
from connectors.mcp.servers import SERVERS

def connection(name, interactive=False):
    server = SERVERS[name]
    found = {"transport": "streamable_http", "url": server["url"]}
    if server["auth"] == "oauth":
        found["auth"] = auth.provider(name, server["url"], interactive, server.get("scope"))
    return found

def is_write(tool):
    # MCP servers mark the tools that only read; every other tool waits for the user's approval
    return not (tool.metadata or {}).get("readOnlyHint", False)

async def server_tools(name, interactive=False):
    # tool names get the server's id in front ("github_search_issues"), so two servers never clash
    client = MultiServerMCPClient({name: connection(name, interactive)}, tool_name_prefix=True)
    return await client.get_tools(server_name=name)

async def load_tools(names):
    # every tool of the connected servers, and the names of the ones that change something.
    # A server that doesn't answer is left out, so the others still work.
    found = await asyncio.gather(*(server_tools(n) for n in names), return_exceptions=True)
    tools, failed = [], []
    for name, result in zip(names, found):
        if isinstance(result, Exception):
            failed.append(name)
        else:
            tools += result
    return tools, {t.name for t in tools if is_write(t)}, failed

ON_DIR = auth.TOKENS_DIR

class McpApp:
    # one MCP server as a Connectors app: connect, check, disconnect
    GROUP = "Other apps"

    def __init__(self, name):
        self.name = name
        # how it shows in Connectors
        self.NAME = SERVERS[name]["name"]
        self.ABOUT = SERVERS[name]["about"]

    def on_file(self):
        return ON_DIR / f"{self.name}.on"

    def connect(self):
        # signs in (if the server needs it) and checks the server answers
        event_loop.run(server_tools(self.name, interactive=True), timeout=auth.SIGN_IN_SECONDS + 30)
        ON_DIR.mkdir(parents=True, exist_ok=True)
        self.on_file().touch()

    def is_connected(self):
        if not self.on_file().exists():
            return False
        return SERVERS[self.name]["auth"] != "oauth" or auth.is_signed_in(self.name)

    def sign_out(self):
        self.on_file().unlink(missing_ok=True)
        auth.forget(self.name)

def apps():
    return {name: McpApp(name) for name in SERVERS}
