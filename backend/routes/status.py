import os

from fastapi import APIRouter, HTTPException, Request

from backend import settings
from config import DEMO, config
from connectors.apps import APPS

router = APIRouter()

def app_state(name):
    # demo mode has made-up mail and no calendar
    if DEMO:
        return "demo" if name == "gmail" else "not_in_demo"
    return "connected" if APPS[name].is_connected() else "not_connected"

def app_states():
    return {name: app_state(name) for name in APPS}

@router.get("/api/status")
def status():
    return {
        "app_name": config.get("app_name", "Assistant"),
        "apps": app_states(),
        "model_key": bool(os.getenv("OPENROUTER_API_KEY")),
        "settings": settings.load(),
    }

@router.put("/api/settings")
async def save_settings(request: Request):
    try:
        return settings.update(await request.json())
    except ValueError as error:
        raise HTTPException(400, str(error))
