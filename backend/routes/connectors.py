import re

from fastapi import APIRouter, HTTPException

from agent import demo
from backend.errors import friendly_error
from backend.routes.status import app_states
from config import DEMO
from connectors.apps import APPS
from connectors.gmail import read as gmail
from connectors.google_auth import get_credentials

router = APIRouter()

MAIL_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

def check_app(app):
    if app not in APPS or DEMO:
        raise HTTPException(404, "There is no app with that name to connect.")

@router.post("/api/connectors/{app}/connect")
def connect(app: str):
    check_app(app)
    try:
        get_credentials(app)
    except Exception as error:
        raise HTTPException(400, f"Google sign-in didn't finish ({type(error).__name__}). Try again.")
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
        found = demo.find(mail_id) if DEMO else gmail.read(mail_id)
    except Exception as error:
        raise HTTPException(502, friendly_error(error))
    if not found:
        raise HTTPException(404, "No mail with that id.")
    return found | {"demo": DEMO}
