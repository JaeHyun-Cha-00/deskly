from datetime import date, datetime

# What the screen shows for a finished step: one short result line, and cards for the mails,
# events and files it found. Summaries only: never a mail's body.

def done(result, mails=(), events=(), files=()):
    return {"result": result, "mails": list(mails), "events": list(events), "files": list(files)}

def plural(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")

def as_text(content):
    # MCP tools may answer with a list of parts
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)

def first_line(content):
    # for a tool with no cards: the first line is enough for the step list
    text = as_text(content).strip()
    return done(text.splitlines()[0][:120] if text else "Done")

def day_name(day):
    try:
        return date.fromisoformat(day).strftime("%a, %b %-d")
    except ValueError:
        return day

def show_time(text):
    # "2026-11-17T15:00" becomes "Tue, Nov 17, 3:00 PM"; a plain day stays a day
    try:
        if len(text) == 10:
            return date.fromisoformat(text).strftime("%a, %b %-d")
        return datetime.fromisoformat(text).strftime("%a, %b %-d, %-I:%M %p")
    except ValueError:
        return text

def mail_card(mail):
    sender = mail.get("from", "").split("<")[0].strip().strip('"')
    if "draft_id" in mail:
        # a draft is from the user; who it's going to says more
        sender = f"Draft to {mail.get('to') or 'nobody yet'}"
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

def file_card(item):
    return {key: item.get(key) for key in ("path", "short", "name", "kind", "size", "modified")}
