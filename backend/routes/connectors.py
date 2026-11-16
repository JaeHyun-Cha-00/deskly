import re
import subprocess

from fastapi import APIRouter, HTTPException, Request

from agent import demo
from backend.errors import friendly_error
from backend.routes.status import app_states
from config import DEMO
from connectors.apps import APPS
from connectors.files import client as files
from connectors.files.guard import safe_path
from connectors.gmail import read as gmail

router = APIRouter()

MAIL_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

def check_app(app):
    if app not in APPS or DEMO:
        raise HTTPException(404, "There is no app with that name to connect.")

@router.post("/api/connectors/{app}/connect")
def connect(app: str):
    check_app(app)
    try:
        APPS[app].connect()
    except Exception as error:
        raise HTTPException(400, f"Connecting didn't finish ({type(error).__name__}). Try again.")
    return {"apps": app_states()}

@router.post("/api/connectors/{app}/disconnect")
def disconnect(app: str):
    check_app(app)
    APPS[app].sign_out()
    return {"apps": app_states()}

@router.get("/api/mail/{mail_id}")
def mail(mail_id: str):
    if not MAIL_ID.fullmatch(mail_id):
        raise HTTPException(400, "That is not a mail id.")
    try:
        found = demo.find(mail_id) if DEMO else gmail.message(mail_id)
    except Exception as error:
        raise HTTPException(502, friendly_error(error))
    if not found:
        raise HTTPException(404, "No mail with that id.")
    return found | {"demo": DEMO}

@router.post("/api/files/reveal")
async def reveal(request: Request):
    # shows a file in Finder; the same checks as the agent's tools, so the page can't open more
    if DEMO or not files.is_connected():
        raise HTTPException(403, "Files aren't connected.")
    path = str((await request.json()).get("path", ""))
    try:
        real = safe_path(path)
    except (PermissionError, FileNotFoundError) as error:
        raise HTTPException(400, str(error))
    subprocess.run(["open", "-R", str(real)], check=False, timeout=10)
    return {"ok": True}
