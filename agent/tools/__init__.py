from agent.tools.calendar import CALENDAR_TOOLS, CALENDAR_WRITE_TOOLS
from agent.tools.files import FILES_TOOLS
from agent.tools.gmail import GMAIL_TOOLS

TOOLS_BY_CONNECTOR = {
    "gmail": GMAIL_TOOLS,
    "calendar": CALENDAR_TOOLS,
    "files": FILES_TOOLS,
}

# every tool that changes something; the agent stops and asks before each call
WRITE_TOOLS = CALENDAR_WRITE_TOOLS

def tools_for(connectors):
    # MCP servers' tools are loaded from the servers themselves (connectors/mcp)
    return [tool for name in connectors for tool in TOOLS_BY_CONNECTOR.get(name, [])]
