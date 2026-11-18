from fastapi import APIRouter, HTTPException, Request

from agent import memory

router = APIRouter()

def everything():
    return memory.load() | {"max": memory.MAX_FACTS}

def changed(action, *args):
    try:
        action(*args)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return everything()

@router.get("/api/memory")
def show():
    return everything()

@router.put("/api/memory/on")
async def turn(request: Request):
    return changed(memory.turn, bool((await request.json()).get("on")))

@router.put("/api/memory/{fact_id}")
async def edit(fact_id: str, request: Request):
    return changed(memory.edit, fact_id, str((await request.json()).get("text", "")))

@router.delete("/api/memory/{fact_id}")
def remove(fact_id: str):
    return changed(memory.remove, fact_id)

@router.delete("/api/memory")
def clear():
    return changed(memory.clear)
