import json
import queue
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from agent.tools import app_name
from backend import history, runner

router = APIRouter()

# about 5k tokens: enough for a long paste, without filling the model's context with one message
MAX_MESSAGE_CHARS = 20000

def chat_id_or_400(chat_id):
    try:
        history.path(chat_id)
    except ValueError:
        raise HTTPException(400, "That is not a chat id.") from None
    return chat_id

def stream(out):
    # the answer's events as Server-Sent Events, until the runner puts None
    while (event := out.get()) is not None:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

@router.get("/api/chats")
def chats():
    return history.list_chats()

@router.get("/api/chats/{chat_id}")
def open_chat(chat_id: str):
    chat = history.load(chat_id_or_400(chat_id))
    # steps saved before steps knew their app get it now
    for turn in chat["turns"]:
        for step in turn["steps"]:
            step.setdefault("app", app_name(step.get("tool", "")))
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
    if len(text) > MAX_MESSAGE_CHARS:
        raise HTTPException(400, f"That message is too long. Keep it under {MAX_MESSAGE_CHARS:,} characters.")

    # its own thread, so the answer is saved even if the page stops listening
    out = queue.Queue()
    threading.Thread(target=runner.answer, args=(chat_id, text, out), daemon=True).start()

    return StreamingResponse(stream(out), media_type="text/event-stream")

def clean_decision(raw):
    # only the three answers the approval card offers, with the fields each one needs
    kind = raw.get("type") if isinstance(raw, dict) else None
    if kind == "approve":
        return {"type": "approve"}
    if kind == "reject":
        message = str(raw.get("message", "")).strip()[:500]
        return {"type": "reject", "message": message} if message else {"type": "reject"}
    if kind == "edit":
        action = raw.get("edited_action") or {}
        args = action.get("args")
        if not isinstance(action.get("name"), str) or not isinstance(args, dict):
            raise HTTPException(400, "An edit needs the action's name and details.")
        # the card edits plain text and numbers only
        if not all(isinstance(k, str) and isinstance(v, str | int | float | bool) for k, v in args.items()):
            raise HTTPException(400, "An edit can only change text and numbers.")
        return {"type": "edit", "edited_action": {"name": action["name"], "args": args}}
    raise HTTPException(400, "Approve, edit or reject.")

@router.post("/api/chats/{chat_id}/decide")
async def decide(chat_id: str, request: Request):
    body = await request.json()
    raw = body.get("decisions")
    if not isinstance(raw, list) or not raw:
        raise HTTPException(400, "Send a decision.")
    decisions = [clean_decision(d) for d in raw]

    out = queue.Queue()
    threading.Thread(target=runner.decide, args=(chat_id_or_400(chat_id), decisions, out), daemon=True).start()
    return StreamingResponse(stream(out), media_type="text/event-stream")

@router.post("/api/chats/{chat_id}/stop")
def stop(chat_id: str):
    runner.stopping.add(chat_id_or_400(chat_id))
    return {"ok": True}
