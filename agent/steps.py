from datetime import date, datetime

from connectors.mcp.servers import SERVERS

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

def mcp_tool(name):
    # "github_search_issues" becomes ("GitHub", "search issues") for an MCP server's tool
    for server, info in SERVERS.items():
        if name.startswith(f"{server}_"):
            return info["name"], name[len(server) + 1:].replace("_", " ")
    return None

def as_text(content):
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)

FILE_TOOLS = {"find_files", "list_folder", "read_file", "file_info", "disk_usage"}

def done(result, mails=(), events=(), files=()):
    return {"result": result, "mails": list(mails), "events": list(events), "files": list(files)}

def file_card(item):
    return {key: item.get(key) for key in ("path", "short", "name", "kind", "size", "modified")}

def file_label(name, args):
    where = args.get("folder") or args.get("path") or "~"
    if name == "find_files":
        kind = f" ({args['kind']})" if args.get("kind") else ""
        return f"Searched your files for “{args.get('query', '')}”{kind}"
    if name == "list_folder":
        return f"Looked in {where}"
    if name == "read_file":
        return f"Opened {where.rsplit('/', 1)[-1]}"
    if name == "file_info":
        return f"Checked {where.rsplit('/', 1)[-1]}"
    return f"Measured what takes space in {where}"

def step_label(call):
    args = call["args"]
    if call["name"] in FILE_TOOLS:
        return file_label(call["name"], args)
    if call["name"] == "list_events":
        return calendar_label(args)
    if call["name"] == "list_calendars":
        return "Looked at your list of calendars"
    if call["name"] == "get_event":
        return "Opened an event"
    if call["name"] == "create_event":
        return f"Add “{args.get('title', '')}” to your calendar"
    if call["name"] == "search_threads":
        query = args.get("query", "").strip()
        return f"Searched your mail for “{query}”" if query else "Looked through your newest mail"
    if call["name"] == "get_thread":
        return "Opened a conversation"
    if call["name"] == "get_message":
        return "Opened a mail"
    if call["name"] == "list_labels":
        return "Looked at your mail labels"
    if call["name"] == "list_drafts":
        query = args.get("query", "").strip()
        return f"Searched your drafts for “{query}”" if query else "Looked at your drafts"
    if call["name"] == "get_draft":
        return "Opened a draft"
    if call["name"] == "remember":
        return "Saved to memory"
    if call["name"] == "forget":
        return "Removed from memory"
    found = mcp_tool(call["name"])
    if found:
        return f"Used {found[0]}: {found[1]}"
    return f"Used {call['name']}"

def show_time(text):
    # "2026-11-17T15:00" becomes "Tue, Nov 17, 3:00 PM"; a plain day stays a day
    try:
        if len(text) == 10:
            return date.fromisoformat(text).strftime("%a, %b %-d")
        return datetime.fromisoformat(text).strftime("%a, %b %-d, %-I:%M %p")
    except ValueError:
        return text

def approval_text(call):
    # the sentence on the approval card: what will happen if the user says yes
    args = call["args"]
    if call["name"] == "create_event":
        start, end = show_time(args.get("start", "")), show_time(args.get("end", ""))
        place = f" at {args['location']}" if args.get("location") else ""
        # "Tue, Nov 17, 3:00 PM to 4:00 PM" when it starts and ends on the same day
        same_day = start.rsplit(", ", 1)[0] == end.rsplit(", ", 1)[0] and start != end
        days = start if start == end else f"{start} to {end.rsplit(', ', 1)[1]}" if same_day else f"{start} to {end}"
        return f"Add “{args.get('title', '')}” to your calendar, {days}{place}."
    found = mcp_tool(call["name"])
    if found:
        return f"{found[0]}: {found[1]}. Check the details below."
    return f"Run {call['name']}."

def plural(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")

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

def step_result(tool, content, artifact=None):
    # returns the short result and the cards for the screen: mails, events and files
    if tool in FILE_TOOLS and artifact is not None:
        if tool == "read_file" or tool == "file_info":
            return done(artifact[0]["name"] if artifact else "", files=[file_card(f) for f in artifact])
        if tool == "disk_usage":
            return done(content.split(" (", 1)[0], files=[file_card(f) for f in artifact])
        return done(plural(len(artifact), "item" if tool == "list_folder" else "file"), files=[file_card(f) for f in artifact])
    if tool == "list_events" and artifact is not None:
        # the model got short lines; the full events come in the artifact
        return done(f"{len(artifact)} event" + ("" if len(artifact) == 1 else "s"), [], [event_card(e) for e in artifact])
    if tool == "create_event" and artifact:
        return done(f"Added “{artifact[0].get('title') or '(no title)'}”", [], [event_card(artifact[0])])
    if tool == "get_event" and artifact:
        return done(artifact[0].get("title") or "(no title)", [], [event_card(artifact[0])])
    if tool == "list_calendars" and artifact is not None:
        return done(plural(len(artifact), "calendar"), [], [])
    if tool == "search_threads" and artifact is not None:
        return done(plural(len(artifact), "conversation"), [mail_card(m) for m in artifact], [])
    if tool == "list_drafts" and artifact is not None:
        return done(plural(len(artifact), "draft"), [mail_card(m) for m in artifact], [])
    if tool == "list_labels" and artifact is not None:
        return done(plural(len(artifact), "label"), [], [])
    if tool in ("get_thread", "get_message", "get_draft") and artifact:
        cards = [mail_card(m) for m in artifact]
        result = f"{cards[-1]['from']}: {cards[-1]['subject']}".strip(": ")
        if len(cards) > 1:
            result += f" ({len(cards)} mails)"
        return done(result, cards, [])
    if tool in ("remember", "forget") and artifact:
        # the fact itself, so the user sees exactly what was kept or dropped
        return done(f"“{artifact[0]['text']}”")
    # any other tool: the first line is enough for the routing slip
    text = as_text(content).strip()
    return done(text.splitlines()[0][:120] if text else "Done")
