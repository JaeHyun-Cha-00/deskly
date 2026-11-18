import threading
import time
import uuid
from collections import defaultdict

from agent import memory
from agent.agent import CHECKPOINTS, connected, get_agent, stream_chat, trim_old_results
from backend import history, settings
from backend.errors import friendly_error
from connectors import event_loop

stopping = set()

# one lock per chat: a new question waits until the previous answer is saved
locks = defaultdict(threading.Lock)

# answers that stopped to ask the user before a write tool: chat id -> the paused run's id.
# Kept in memory only, so closing the app lets go of them.
paused = {}

DECIDED = {"approve": "approved", "edit": "edited", "reject": "rejected"}

def record(turn, event):
    if event["type"] == "step":
        # picking up a paused run sends the paused step again
        if any(s["id"] == event["id"] for s in turn["steps"]):
            return
        turn["steps"].append({"id": event["id"], "label": event["label"], "done": False, "tool": event.get("tool", ""), "app": event.get("app", ""), "result": "", "mails": [], "events": [], "files": []})
        # text written before a step was the agent thinking aloud
        turn["draft"] = ""
    if event["type"] == "step_done":
        step = next((s for s in turn["steps"] if s["id"] == event["id"]), None)
        if step:
            step.update(done=True, tool=event["tool"], result=event["result"], mails=event["mails"], events=event["events"], files=event["files"])
    if event["type"] == "token":
        turn["draft"] += event["text"]
    if event["type"] == "answer":
        turn["answer"] = event["text"]
    if event["type"] == "approval":
        turn["approval"] = {"requests": event["requests"], "state": "waiting"}
    if event["type"] == "usage":
        # the last model call holds the most, so it is the one to show
        turn["context"] = {"tokens": event["tokens"], "limit": event["limit"]}

def let_go(chat_id, chat):
    # a new question drops an answer that was still waiting for approval
    run_id = paused.pop(chat_id, None)
    if run_id:
        CHECKPOINTS.delete_thread(run_id)
    last = chat["turns"][-1] if chat["turns"] else {}
    if (last.get("approval") or {}).get("state") == "waiting":
        last["approval"]["state"] = "expired"

def run(chat_id, chat, turn, run_id, make_events, out):
    # streams one run of the agent into `turn` and `out`, then saves the chat
    stopping.discard(chat_id)
    turn["draft"] = ""
    seen = {"waiting": False}

    async def follow():
        chosen = settings.load()
        runner = await get_agent(chosen["length"], connected(), use_memory=memory.is_on())
        async for event in make_events(runner):
            if chat_id in stopping:
                return
            if event["type"] == "history":
                # a paused answer isn't finished, so the agent's memory waits for the decision
                if not seen["waiting"]:
                    history.remember(chat, event["messages"])
                continue
            if event["type"] == "approval":
                seen["waiting"] = True
            record(turn, event)
            out.put(event)

    finished = False
    began = time.monotonic()
    try:
        event_loop.run(follow())
        finished = chat_id not in stopping
    except Exception as error:
        turn["error"] = friendly_error(error)
        out.put({"type": "error", "message": turn["error"]})

    # time spent working; a paused answer adds the rest after the user decides
    turn["seconds"] = round(turn.get("seconds", 0) + time.monotonic() - began, 1)
    waiting = seen["waiting"]
    if waiting and finished and not turn["error"]:
        paused[chat_id] = run_id
    else:
        CHECKPOINTS.delete_thread(run_id)
        waiting = False
        if (turn.get("approval") or {}).get("state") == "waiting":
            turn["approval"]["state"] = "expired"

    # a stopped answer keeps what was written; the agent's memory skips it
    if not finished and not turn["error"]:
        turn["stopped"] = True
        turn["answer"] = turn["answer"] or turn["draft"].strip()
    elif not turn["answer"] and not turn["error"] and not waiting:
        turn["error"] = "No reply came back."
    del turn["draft"]
    stopping.discard(chat_id)

    chat["turns"].append(turn)
    chat["title"] = chat["title"] or turn["user"][:60]
    history.save(chat)
    out.put({"type": "done", "stopped": turn["stopped"], "waiting": waiting, "seconds": turn["seconds"], "chat": {"id": chat["id"], "title": chat["title"], "updated": chat["updated"]}})
    out.put(None)

def answer(chat_id, text, out):
    with locks[chat_id]:
        chat = history.load(chat_id)
        let_go(chat_id, chat)
        turn = {"user": text, "at": history.now(), "steps": [], "answer": "", "error": "", "stopped": False, "approval": None}
        run_id = str(uuid.uuid4())
        # the last question's results stay whole, for follow-ups like "what did the second one say?"
        past = trim_old_results(history.messages(chat))
        run(chat_id, chat, turn, run_id, lambda runner: stream_chat(past, text, runner, run_id), out)

def check_decisions(requests, decisions):
    # one decision per request, and an edit may change the details but not the tool
    if len(decisions) != len(requests):
        raise ValueError("Answer every request on the card.")
    for request, decision in zip(requests, decisions):
        if decision["type"] == "edit" and decision["edited_action"]["name"] != request["name"]:
            raise ValueError("An edit can't change what kind of action it is.")

def decide(chat_id, decisions, out):
    with locks[chat_id]:
        chat = history.load(chat_id)
        last = chat["turns"][-1] if chat["turns"] else {}
        run_id = paused.get(chat_id)
        if not run_id or (last.get("approval") or {}).get("state") != "waiting":
            # the app was closed, or a newer question replaced it
            let_go(chat_id, chat)
            history.save(chat)
            out.put({"type": "expired", "message": "This request expired. Ask again and I'll prepare it again."})
            out.put(None)
            return
        try:
            check_decisions(last["approval"]["requests"], decisions)
        except ValueError as error:
            out.put({"type": "error", "message": str(error)})
            out.put(None)
            return

        paused.pop(chat_id)
        turn = chat["turns"].pop()
        turn["approval"]["state"] = DECIDED[decisions[0]["type"]]
        turn["approval"]["decisions"] = decisions
        out.put({"type": "decided", "state": turn["approval"]["state"]})
        run(chat_id, chat, turn, run_id, lambda runner: stream_chat([], "", runner, run_id, decisions), out)
