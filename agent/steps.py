import json

# Summaries only: never the mail body.

def step_label(call):
    args = call["args"]
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

def step_result(content):
    try:
        data = json.loads(content)
    except ValueError:
        return content[:120], []
    if isinstance(data, list):
        return f"{len(data)} mail" + ("" if len(data) == 1 else "s"), [mail_card(m) for m in data]
    card = mail_card(data)
    return f"{card['from']}: {card['subject']}".strip(": "), [card]
