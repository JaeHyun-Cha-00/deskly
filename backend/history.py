import json
import uuid
from datetime import datetime
from langchain_core.messages import messages_from_dict, messages_to_dict

from config import CHATS_DIR as CHATS, write_private

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
    write_private(path(chat["id"]), json.dumps(chat, ensure_ascii=False))

def messages(chat):
    return messages_from_dict(chat["messages"])

def remember(chat, messages):
    chat["messages"] = messages_to_dict(messages)

# file -> (when it last changed, its id, title and date), so listing chats doesn't read
# every chat in full each time, only the ones that changed
SUMMARIES = {}

def summary(file):
    changed = file.stat().st_mtime_ns
    known = SUMMARIES.get(file)
    if known and known[0] == changed:
        return known[1]
    try:
        chat = json.loads(file.read_text())
        found = {"id": chat["id"], "title": chat["title"], "updated": chat["updated"]}
    except (ValueError, KeyError, OSError):
        # a damaged file is left out, so it can't hide every other chat
        found = None
    SUMMARIES[file] = (changed, found)
    return found

def list_chats():
    chats = [found for file in CHATS.glob("*.json") if (found := summary(file))]
    chats.sort(key=lambda chat: chat["updated"], reverse=True)
    return chats

def rename(chat_id, title):
    chat = load(chat_id)
    chat["title"] = title
    save(chat)

def delete(chat_id):
    path(chat_id).unlink(missing_ok=True)

def delete_all():
    for file in CHATS.glob("*.json"):
        file.unlink()
