import os

from fastapi import APIRouter, HTTPException, Request

from backend import settings
from config import DEMO, config
from connectors.gmail.client import is_connected

router = APIRouter()

def gmail_state():
    return "demo" if DEMO else ("connected" if is_connected() else "not_connected")

@router.get("/api/status")
def status():
    return {
        "app_name": config.get("app_name", "Assistant"),
        "gmail": gmail_state(),
        "model_key": bool(os.getenv("DEEPINFRA_API_KEY")),
        "settings": settings.load(),
    }

@router.put("/api/settings")
async def save_settings(request: Request):
    try:
        return settings.update(await request.json())
    except ValueError as error:
        raise HTTPException(400, str(error))
