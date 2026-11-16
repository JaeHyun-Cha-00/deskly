import json
from datetime import date

# Summaries only: never the mail body.

def day_name(day):
    try:
        return date.fromisoformat(day).strftime("%a, %b %-d")
    except ValueError:
        return day

def calendar_label(args):
    query = args.get("query", "").strip()
    start, end = day_name(args.get("start_day", "")), day_name(args.get("end_day", ""))
    days = start if start == end else f"{start} to {end}"
    return f"Searched your calendar for “{query}”, {days}" if query else f"Looked at your calendar, {days}"

def step_label(call):
    args = call["args"]
    if call["name"] == "list_events":
        return calendar_label(args)
    if call["name"] == "search_emails":
        query = args.get("query", "").strip()
        return f"Searched your mail for “{query}”" if query else "Looked through your newest mail"
    if call["name"] == "read_email":
        return "Opened a mail"
    return f"Used {call['name']}"

def mail_card(mail):
    sender = mail.get("from", "").split("<")[0].strip().strip('"')
    return {
        "id": mail["id"],
        "from": sender or mail.get("from", ""),
        "subject": mail.get("subject", ""),
        "date": mail.get("date", ""),
        "unread": mail.get("unread", False),
        "snippet": mail.get("snippet", "")[:160],
    }

def event_card(event):
    link = event.get("link", "")
    return {
        "id": event["id"],
        "title": event.get("title", ""),
        "start": event.get("start", ""),
        "end": event.get("end", ""),
        "all_day": event.get("all_day", False),
        "location": event.get("location", "")[:120],
        # only Google's own https links become links on the screen
        "link": link if link.startswith("https://www.google.com/calendar/") else "",
    }

def step_result(tool, content, artifact=None):
    # returns the short result, the mail cards and the event cards
    if tool == "list_events" and artifact is not None:
        # the model got short lines; the full events come in the artifact
        return f"{len(artifact)} event" + ("" if len(artifact) == 1 else "s"), [], [event_card(e) for e in artifact]
    try:
        data = json.loads(content)
    except ValueError:
        return content[:120], [], []
    if isinstance(data, list):
        return f"{len(data)} mail" + ("" if len(data) == 1 else "s"), [mail_card(m) for m in data], []
    card = mail_card(data)
    return f"{card['from']}: {card['subject']}".strip(": "), [card], []
