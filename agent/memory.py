import json
import re
import threading
import uuid
from datetime import datetime

from config import MEMORY_FILE, write_private

# Facts the agent remembers about the user across chats. Every fact goes into the system
# prompt, so the list stays short.
MAX_FACTS = 50
MAX_CHARS = 200

# things that must never be kept: long numbers (cards, accounts) and key-like strings
SECRET = re.compile(r"\d[\d -]{8,}\d|\b(sk|pk|ghp|gho|xox[abp])[-_][A-Za-z0-9_-]{8,}|password|passcode", re.I)

# the agent's tools and the Memory window can change the file at the same time
LOCK = threading.RLock()

def load():
    saved = json.loads(MEMORY_FILE.read_text()) if MEMORY_FILE.exists() else {}
    return {"on": saved.get("on", True), "facts": saved.get("facts", [])}

def save(memory):
    write_private(MEMORY_FILE, json.dumps(memory, indent=1))

def is_on():
    return load()["on"]

def facts():
    return load()["facts"]

def clean(text):
    text = " ".join(str(text).split())
    if not text:
        raise ValueError("A memory can't be empty.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"Keep a memory to one short sentence (under {MAX_CHARS} characters).")
    if SECRET.search(text):
        raise ValueError("Passwords, keys and card or account numbers are never saved to memory.")
    return text

def add(text):
    with LOCK:
        memory = load()
        text = clean(text)
        if any(f["text"].lower() == text.lower() for f in memory["facts"]):
            raise ValueError("That is already in memory.")
        if len(memory["facts"]) >= MAX_FACTS:
            raise ValueError(f"Memory is full ({MAX_FACTS} facts). Ask the user which one to forget.")
        fact = {"id": uuid.uuid4().hex[:8], "text": text, "at": datetime.now().astimezone().isoformat(timespec="seconds")}
        memory["facts"].append(fact)
        save(memory)
        return fact

def find(memory, fact_id):
    fact = next((f for f in memory["facts"] if f["id"] == fact_id), None)
    if not fact:
        raise ValueError(f"No memory has the id {fact_id!r}.")
    return fact

def edit(fact_id, text):
    with LOCK:
        memory = load()
        find(memory, fact_id)["text"] = clean(text)
        save(memory)

def remove(fact_id):
    with LOCK:
        memory = load()
        fact = find(memory, fact_id)
        memory["facts"].remove(fact)
        save(memory)
        return fact

def clear():
    with LOCK:
        save(load() | {"facts": []})

def turn(on):
    with LOCK:
        save(load() | {"on": bool(on)})
