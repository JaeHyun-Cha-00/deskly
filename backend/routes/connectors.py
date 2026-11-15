import re

from fastapi import APIRouter, HTTPException

from agent import demo
from backend.errors import friendly_error
from backend.routes.status import gmail_state
from config import DEMO
from connectors.gmail import read as gmail
from connectors.gmail.client import sign_out
from connectors.google_auth import get_credentials

router = APIRouter()

MAIL_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

@router.post("/api/gmail/connect")
def connect_gmail():
    try:
        get_credentials()
    except Exception as error:
        raise HTTPException(400, f"Google sign-in didn't finish ({type(error).__name__}). Try again.")
    return {"gmail": gmail_state()}

@router.post("/api/gmail/disconnect")
def disconnect_gmail():
    sign_out()
    return {"gmail": gmail_state()}

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
