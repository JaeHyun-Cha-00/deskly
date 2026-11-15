from agent.tools.gmail import GMAIL_TOOLS

TOOLS_BY_CONNECTOR = {
    "gmail": GMAIL_TOOLS,
}

def tools_for(connectors):
    return [tool for name in connectors for tool in TOOLS_BY_CONNECTOR[name]]
