import json
import queue
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend import history, runner

router = APIRouter()

def chat_id_or_400(chat_id):
    try:
        history.path(chat_id)
    except ValueError:
        raise HTTPException(400, "That is not a chat id.")
    return chat_id

@router.get("/api/chats")
def chats():
    return history.list_chats()

@router.get("/api/chats/{chat_id}")
def open_chat(chat_id: str):
    chat = history.load(chat_id_or_400(chat_id))
    return {key: chat[key] for key in ("id", "title", "updated", "turns")}

@router.patch("/api/chats/{chat_id}")
async def rename_chat(chat_id: str, request: Request):
    title = str((await request.json()).get("title", "")).strip()[:80]
    if not title or not history.exists(chat_id_or_400(chat_id)):
        raise HTTPException(400, "Give the chat a name.")
    history.rename(chat_id, title)
    return {"ok": True}

@router.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    history.delete(chat_id_or_400(chat_id))
    return {"ok": True}

@router.delete("/api/chats")
def delete_all_chats():
    history.delete_all()
    return {"ok": True}

@router.post("/api/chat")
async def ask(request: Request):
    body = await request.json()
    chat_id, text = chat_id_or_400(str(body.get("chat_id", ""))), str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(400, "Write a message first.")

    # its own thread, so the answer is saved even if the page stops listening
    out = queue.Queue()
    threading.Thread(target=runner.answer, args=(chat_id, text, out), daemon=True).start()

    def events():
        while (event := out.get()) is not None:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

@router.post("/api/chats/{chat_id}/stop")
def stop(chat_id: str):
    runner.stopping.add(chat_id_or_400(chat_id))
    return {"ok": True}
