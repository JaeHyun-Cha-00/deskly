from connectors.gmail.client import body_text, get_service, header

HEADERS = ["From", "To", "Cc", "Subject", "Date"]
# a long conversation sends the newest mail in full and shortens the older ones
OLDER_BODY_CHARS = 1500

def meta(message):
    # the short facts about one mail, from a "metadata" or "full" message
    return {
        "id": message["id"],
        "thread_id": message.get("threadId", ""),
        "from": header(message, "From"),
        "to": header(message, "To"),
        "cc": header(message, "Cc"),
        "subject": header(message, "Subject"),
        "date": header(message, "Date"),
        # milliseconds since 1970, easier to sort and format than the Date header
        "time": int(message.get("internalDate", 0)),
        "snippet": message.get("snippet", ""),
        "unread": "UNREAD" in message.get("labelIds", []),
    }

def attachments(payload):
    names, parts = [], [payload]
    while parts:
        part = parts.pop()
        parts += part.get("parts", [])
        if part.get("filename"):
            names.append(part["filename"])
    return names

def full(message):
    return meta(message) | {"body": body_text(message["payload"]), "attachments": attachments(message["payload"])}

def get_many(requests):
    # sends many Gmail requests in one trip to Google and returns the answers in order;
    # a request that failed (e.g. the mail was just deleted) gives None
    answers = {}
    def keep(request_id, answer, error):
        answers[request_id] = None if error else answer
    batch = get_service().new_batch_http_request(callback=keep)
    for number, request in enumerate(requests):
        batch.add(request, request_id=str(number))
    if requests:
        batch.execute()
    return [answers.get(str(number)) for number in range(len(requests))]

def search_threads(query, max_results=20):
    # each conversation is shown by its newest mail
    threads = get_service().users().threads()
    found = threads.list(userId="me", q=query, maxResults=max_results).execute()
    details = get_many([
        threads.get(userId="me", id=item["id"], format="metadata", metadataHeaders=HEADERS)
        for item in found.get("threads", [])
    ])
    results = []
    for thread in details:
        messages = (thread or {}).get("messages", [])
        if not messages:
            continue
        newest = meta(messages[-1])
        newest["count"] = len(messages)
        newest["unread"] = any("UNREAD" in m.get("labelIds", []) for m in messages)
        results.append(newest)
    return results

def thread(thread_id):
    found = get_service().users().threads().get(userId="me", id=thread_id, format="full").execute()
    messages = [full(m) for m in found.get("messages", [])]
    for message in messages[:-1]:
        message["body"] = message["body"][:OLDER_BODY_CHARS]
    return messages

def message(message_id):
    found = get_service().users().messages().get(userId="me", id=message_id, format="full").execute()
    return full(found)

def labels():
    found = get_service().users().labels().list(userId="me").execute()
    return [{"id": label["id"], "name": label["name"], "type": label.get("type", "")} for label in found.get("labels", [])]

def drafts(query="", max_results=20):
    drafts = get_service().users().drafts()
    found = drafts.list(userId="me", q=query or None, maxResults=max_results).execute()
    details = get_many([drafts.get(userId="me", id=item["id"], format="metadata") for item in found.get("drafts", [])])
    return [meta(d["message"]) | {"draft_id": d["id"]} for d in details if d]

def draft(draft_id):
    found = get_service().users().drafts().get(userId="me", id=draft_id, format="full").execute()
    return full(found["message"]) | {"draft_id": found["id"]}
