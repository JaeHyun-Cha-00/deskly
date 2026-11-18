import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import write_private
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

def short_name(tool, name):
    # the server's own name for a tool: "github_search_issues" becomes "search_issues"
    return tool.name.removeprefix(f"{name}_")

def tools_file(name):
    return auth.TOKENS_DIR / f"{name}_tools.json"

def chosen_tools(name):
    # the tools the user turned on in Connectors; until they choose, the server's recommended
    # set ("tools" in servers.py); None means every tool
    if tools_file(name).exists():
        return set(json.loads(tools_file(name).read_text()))
    keep = SERVERS[name].get("tools")
    return set(keep) if keep else None

def choose_tools(name, names):
    # None goes back to the recommended set
    if names is None:
        tools_file(name).unlink(missing_ok=True)
        return
    write_private(tools_file(name), json.dumps(sorted(names)))

async def server_tools(name, interactive=False, everything=False):
    # tool names get the server's id in front ("github_search_issues"), so two servers never clash.
    # Only the chosen tools, unless `everything` (for the Tools screen in Connectors).
    client = MultiServerMCPClient({name: connection(name, interactive)}, tool_name_prefix=True)
    tools = await client.get_tools(server_name=name)
    keep = None if everything else chosen_tools(name)
    if keep is not None:
        tools = [t for t in tools if short_name(t, name) in keep]
    return tools

def tool_tokens(tool):
    # about how many tokens the tool's description costs with every question
    import tiktoken
    from langchain_core.utils.function_calling import convert_to_openai_tool
    return len(tiktoken.get_encoding("o200k_base").encode(json.dumps(convert_to_openai_tool(tool))))

def describe_tools(name):
    # every tool the server offers, for the Tools screen: on or off, reads or writes, its cost
    tools = event_loop.run(server_tools(name, everything=True), timeout=60)
    keep = chosen_tools(name)
    recommended = SERVERS[name].get("tools")
    found = []
    for tool in tools:
        short = short_name(tool, name)
        about = " ".join((tool.description or "").split())
        found.append({
            "name": short,
            "title": short.removeprefix(f"{name}-").replace("_", " ").replace("-", " "),
            "about": about[:160] + ("…" if len(about) > 160 else ""),
            "write": is_write(tool),
            "tokens": tool_tokens(tool),
            "on": keep is None or short in keep,
            "recommended": recommended is None or short in recommended,
        })
    return found

def needs_sign_in(error):
    # the MCP client wraps errors (sometimes in groups), so look through all of them
    if isinstance(error, auth.SignInNeeded):
        return True
    inner = [*getattr(error, "exceptions", []), error.__cause__, error.__context__]
    return any(needs_sign_in(e) for e in inner if e is not None and e is not error)

async def load_tools(names):
    # every tool of the connected servers, the names of the ones that change something, and
    # why any server was left out ({id: "sign_in" or "no_answer"}), so the others still work
    found = await asyncio.gather(*(server_tools(n) for n in names), return_exceptions=True)
    tools, failed = [], {}
    for name, result in zip(names, found, strict=True):
        if isinstance(result, BaseException):
            failed[name] = "sign_in" if needs_sign_in(result) else "no_answer"
            if failed[name] == "sign_in":
                # the saved sign-in no longer works: show the app as not connected
                McpApp(name).sign_out()
        else:
            tools += result
    return tools, {t.name for t in tools if is_write(t)}, failed

ON_DIR = auth.TOKENS_DIR

class McpApp:
    # one MCP server as a Connectors app: connect, check, disconnect, choose its tools
    GROUP = "Other apps"
    HAS_TOOLS = True

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
