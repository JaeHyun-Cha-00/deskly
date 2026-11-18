from datetime import datetime

from agent.tools import memory, prompt_for

LENGTH = {
    "short": "Keep answers short: a few lines or a short list.",
    "detailed": "Give complete answers with the details that matter, organized with short lists.",
}

NOT_CONNECTED = """No apps are connected yet, so you can't see the user's mail, calendar or files.
Answer like a helpful general assistant. If the user asks about their mail or calendar, tell them
to open Connectors (bottom left) and connect Gmail, Calendar or Files; don't make up mail, events or files."""

def system_prompt(length="short", connectors=(), use_memory=False):
    now = datetime.now().astimezone()
    today = now.strftime("%A, %B %d, %Y, %I:%M %p (%Z)")
    apps = "\n\n".join(prompt_for(name) for name in connectors) or NOT_CONNECTED
    remembered = f"\n\n{memory.prompt()}" if use_memory else ""
    return f"""You are a personal assistant that runs on the user's laptop. It is now {today}.

{apps}{remembered}

{LENGTH[length]} Reply in English."""
