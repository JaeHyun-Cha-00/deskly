import json
import uuid
from datetime import datetime
from langchain_core.messages import messages_from_dict, messages_to_dict

from config import CHATS_DIR as CHATS

def now():
    return datetime.now().isoformat(timespec="seconds")

def path(chat_id):
    # uuid.UUID() rejects anything that isn't a chat id, so a name like "../x" can't reach other files
    return CHATS / f"{uuid.UUID(chat_id)}.json"

def exists(chat_id):
    return path(chat_id).exists()

def load(chat_id):
    if exists(chat_id):
        return json.loads(path(chat_id).read_text())
    return {"id": str(uuid.UUID(chat_id)), "title": "", "created": now(), "updated": now(), "messages": [], "turns": []}

def save(chat):
    chat["updated"] = now()
    CHATS.mkdir(parents=True, exist_ok=True)
    path(chat["id"]).write_text(json.dumps(chat, ensure_ascii=False))

def messages(chat):
    return messages_from_dict(chat["messages"])

def remember(chat, messages):
    chat["messages"] = messages_to_dict(messages)

def list_chats():
    chats = [json.loads(file.read_text()) for file in CHATS.glob("*.json")]
    chats.sort(key=lambda chat: chat["updated"], reverse=True)
    return [{"id": c["id"], "title": c["title"], "updated": c["updated"]} for c in chats]

def rename(chat_id, title):
    chat = load(chat_id)
    chat["title"] = title
    save(chat)

def delete(chat_id):
    path(chat_id).unlink(missing_ok=True)

def delete_all():
    for file in CHATS.glob("*.json"):
        file.unlink()
