from agent.cards import first_line
from agent.tools import calendar, files, gmail, memory, mcp_servers

# Each built-in app keeps everything about itself in its own module: TOOLS, WRITES, NAME,
# PROMPT, label(call), result(tool, content, artifact) and, for write tools, approval(call).
# Adding an app is one new module here plus its connector.
APPS = {"gmail": gmail, "calendar": calendar, "files": files, "memory": memory}

# which app each tool belongs to, e.g. "list_events" -> "calendar"
OWNER = {tool.name: app for app, module in APPS.items() for tool in module.TOOLS}

# every built-in tool that changes something; the agent stops and asks before each call
WRITE_TOOLS = set().union(*(module.WRITES for module in APPS.values()))

def tools_for(connectors):
    # memory's tools come with the memory switch; MCP servers' tools from the servers (connectors/mcp)
    return [tool for name in connectors if name in APPS and name != "memory" for tool in APPS[name].TOOLS]

def prompt_for(connector):
    if connector in APPS:
        return APPS[connector].PROMPT
    return mcp_servers.prompt(connector)

def app_name(tool):
    # the name the screen groups a step under, e.g. "Gmail" or "GitHub"
    if tool in OWNER:
        return APPS[OWNER[tool]].NAME
    server = mcp_servers.server_of(tool)
    return mcp_servers.name(server) if server else "Other"

def step_label(call):
    if call["name"] in OWNER:
        return APPS[OWNER[call["name"]]].label(call)
    server = mcp_servers.server_of(call["name"])
    return mcp_servers.label(call, server) if server else f"Used {call['name']}"

def step_result(tool, content, artifact=None):
    # the short result and the cards for the screen: mails, events and files
    if tool in OWNER:
        found = APPS[OWNER[tool]].result(tool, content, artifact)
    elif mcp_servers.server_of(tool):
        found = mcp_servers.result(tool, content, artifact)
    else:
        found = None
    return found or first_line(content)

def approval_text(call):
    if call["name"] in OWNER:
        return APPS[OWNER[call["name"]]].approval(call)
    server = mcp_servers.server_of(call["name"])
    return mcp_servers.approval(call, server) if server else f"Run {call['name']}."
