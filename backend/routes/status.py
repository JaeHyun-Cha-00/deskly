import os

from fastapi import APIRouter, HTTPException, Request

from backend import settings
from config import config
from connectors.apps import APPS, rows

router = APIRouter()

def app_state(name):
    return "connected" if APPS[name].is_connected() else "not_connected"

def app_states():
    return {name: app_state(name) for name in APPS}

@router.get("/api/status")
def status():
    return {
        "app_name": config.get("app_name", "Assistant"),
        "apps": app_states(),
        # every app, so the screen can build the Connectors window
        "connectors": rows(),
        "model_key": bool(os.getenv("OPENROUTER_API_KEY")),
        # window settings (opacity) only exist in the desktop app
        "desktop": os.getenv("ASSISTANT_DESKTOP") == "1",
        "settings": settings.load(),
    }

@router.put("/api/settings")
async def save_settings(request: Request):
    try:
        return settings.update(await request.json())
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
