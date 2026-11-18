import re
import subprocess

from fastapi import APIRouter, HTTPException, Request

from agent.agent import AGENTS
from backend.errors import friendly_error
from backend.routes.status import app_states
from connectors.apps import APPS
from connectors.files import client as files
from connectors.files.guard import safe_path
from connectors.gmail import read as gmail
from connectors.mcp import client as mcp
from connectors.mcp.servers import SERVERS

router = APIRouter()

MAIL_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

def check_app(app):
    if app not in APPS:
        raise HTTPException(404, "There is no app with that name to connect.")

@router.post("/api/connectors/{app}/connect")
def connect(app: str):
    check_app(app)
    try:
        APPS[app].connect()
    except Exception as error:
        raise HTTPException(400, f"Connecting didn't finish ({type(error).__name__}). Try again.") from error
    return {"apps": app_states()}

@router.post("/api/connectors/{app}/disconnect")
def disconnect(app: str):
    check_app(app)
    APPS[app].sign_out()
    return {"apps": app_states()}

def check_server(app):
    if app not in SERVERS:
        raise HTTPException(404, "Only MCP apps have tools to choose.")
    if not APPS[app].is_connected():
        raise HTTPException(400, "Connect the app first.")

@router.get("/api/connectors/{app}/tools")
def tools(app: str):
    check_server(app)
    try:
        return {"tools": mcp.describe_tools(app)}
    except Exception as error:
        raise HTTPException(502, f"Couldn't get the tools ({type(error).__name__}). Try again.") from error

@router.put("/api/connectors/{app}/tools")
async def choose_tools(app: str, request: Request):
    # {"tools": [names]} turns exactly those on; {"tools": null} goes back to the recommended set
    check_server(app)
    names = (await request.json()).get("tools")
    if names is not None:
        if not isinstance(names, list) or not all(isinstance(n, str) and len(n) < 200 for n in names):
            raise HTTPException(400, "That is not a list of tool names.")
        names = set(names)
    mcp.choose_tools(app, names)
    # the agent is built again with the new tools on the next question
    AGENTS.clear()
    return tools(app)

@router.get("/api/mail/{mail_id}")
def mail(mail_id: str):
    if not MAIL_ID.fullmatch(mail_id):
        raise HTTPException(400, "That is not a mail id.")
    try:
        found = gmail.message(mail_id)
    except Exception as error:
        raise HTTPException(502, friendly_error(error)) from error
    if not found:
        raise HTTPException(404, "No mail with that id.")
    return found

@router.post("/api/files/reveal")
async def reveal(request: Request):
    # shows a file in Finder; the same checks as the agent's tools, so the page can't open more
    if not files.is_connected():
        raise HTTPException(403, "Files aren't connected.")
    path = str((await request.json()).get("path", ""))
    try:
        real = safe_path(path)
    except (PermissionError, FileNotFoundError) as error:
        raise HTTPException(400, str(error)) from error
    subprocess.run(["open", "-R", str(real)], check=False, timeout=10)
    return {"ok": True}
