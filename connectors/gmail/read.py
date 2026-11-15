from connectors.gmail.client import body_text, get_service, header

def search(query, max_results=10):
    service = get_service()
    found = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()

    results = []
    for item in found.get("messages", []):
        message = service.users().messages().get(
            userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        results.append({
            "id": message["id"],
            "from": header(message, "From"),
            "subject": header(message, "Subject"),
            "date": header(message, "Date"),
            "snippet": message.get("snippet", ""),
            "unread": "UNREAD" in message.get("labelIds", []),
        })
    return results

def read(message_id):
    message = get_service().users().messages().get(userId="me", id=message_id, format="full").execute()
    return {
        "id": message["id"],
        "from": header(message, "From"),
        "to": header(message, "To"),
        "subject": header(message, "Subject"),
        "date": header(message, "Date"),
        "body": body_text(message["payload"]),
    }

if __name__ == "__main__":
    for mail in search("", max_results=5):
        print(mail["subject"] or "(no subject)")
