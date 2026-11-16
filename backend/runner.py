import threading
from collections import defaultdict

from agent.agent import build_agent, connected, stream_chat
from backend import history, settings
from backend.errors import friendly_error
from config import DEMO

stopping = set()

# one lock per chat: a new question waits until the previous answer is saved
locks = defaultdict(threading.Lock)

def record(turn, event):
    if event["type"] == "step":
        turn["steps"].append({"id": event["id"], "label": event["label"], "done": False, "tool": "", "result": "", "mails": [], "events": []})
        # text written before a step was the agent thinking aloud
        turn["draft"] = ""
    if event["type"] == "step_done":
        step = next((s for s in turn["steps"] if s["id"] == event["id"]), None)
        if step:
            step.update(done=True, tool=event["tool"], result=event["result"], mails=event["mails"], events=event["events"])
    if event["type"] == "token":
        turn["draft"] += event["text"]
    if event["type"] == "answer":
        turn["answer"] = event["text"]

def answer(chat_id, text, out):
    with locks[chat_id]:
        stopping.discard(chat_id)
        chat = history.load(chat_id)
        turn = {"user": text, "at": history.now(), "steps": [], "answer": "", "error": "", "stopped": False, "draft": ""}
        finished = False
        try:
            chosen = settings.load()
            apps = ("gmail",) if DEMO else connected()
            runner = build_agent(chosen["length"], apps, DEMO)
            for event in stream_chat(history.messages(chat), text, runner):
                if chat_id in stopping:
                    break
                if event["type"] == "history":
                    history.remember(chat, event["messages"])
                    continue
                record(turn, event)
                out.put(event)
            finished = chat_id not in stopping
        except Exception as error:
            turn["error"] = friendly_error(error)
            out.put({"type": "error", "message": turn["error"]})

        # a stopped answer keeps what was written; the agent's memory skips it
        if not finished and not turn["error"]:
            turn["stopped"] = True
            turn["answer"] = turn["answer"] or turn["draft"].strip()
        elif not turn["answer"] and not turn["error"]:
            turn["error"] = "No reply came back."
        del turn["draft"]
        stopping.discard(chat_id)

        chat["turns"].append(turn)
        chat["title"] = chat["title"] or text[:60]
        history.save(chat)
        out.put({"type": "done", "stopped": turn["stopped"], "chat": {"id": chat["id"], "title": chat["title"], "updated": chat["updated"]}})
        out.put(None)
