from datetime import datetime

from langchain.tools import tool

from connectors.gmail import read

SNIPPET_CHARS = 160

def short_time(mail):
    return datetime.fromtimestamp(mail["time"] / 1000).strftime("%a %b %-d %H:%M") if mail["time"] else mail["date"]

def sender(mail):
    # "Prof. Rivera <rivera@uni.edu>" becomes "Prof. Rivera"
    name = mail["from"].split("<")[0].strip().strip('"')
    return name or mail["from"]

def mail_block(mail, id_name="message"):
    # one mail in full, for the model
    lines = [
        f"From: {mail['from']}",
        f"To: {mail['to']}",
    ]
    if mail["cc"]:
        lines.append(f"Cc: {mail['cc']}")
    lines += [f"Date: {short_time(mail)}", f"Subject: {mail['subject'] or '(no subject)'}"]
    if mail["attachments"]:
        lines.append(f"Attachments: {', '.join(mail['attachments'])}")
    mail_id = mail["draft_id"] if id_name == "draft" else mail["id"]
    lines += [f"[{id_name}: {mail_id}]", "", mail["body"] or "(no text)"]
    return "\n".join(lines)

# The model reads the short text; the screen gets the full mails (the "artifact").

@tool(parse_docstring=True, response_format="content_and_artifact")
def search_threads(query: str, max_results: int = 20) -> tuple[str, list]:
    """Search the user's Gmail and list the matching conversations (threads), newest first.

    Uses Gmail search words, e.g. "is:unread newer_than:1d", "from:alice@example.com",
    "subject:invoice", "has:attachment after:2026/11/01". Turn the user's words into these
    before searching. An empty query lists the newest conversations.
    Returns one line per conversation, shown by its newest mail: date, sender, subject,
    a snippet, how many mails it has, whether any is unread, and the thread id.

    Args:
        query: Gmail search words. Use "" for the newest mail.
        max_results: How many conversations to return (1 to 50).
    """
    threads = read.search_threads(query, max_results=min(max(max_results, 1), 50))
    if not threads:
        return "No mail matched.", []
    lines = []
    for mail in threads:
        count = f"{mail['count']} mails" if mail["count"] > 1 else "1 mail"
        unread = ", unread" if mail["unread"] else ""
        snippet = mail["snippet"][:SNIPPET_CHARS]
        lines.append(f"{short_time(mail)}  {sender(mail)}  “{mail['subject'] or '(no subject)'}”  {snippet}  ({count}{unread})  [thread: {mail['thread_id']}]")
    return "\n".join(lines), threads

@tool(parse_docstring=True, response_format="content_and_artifact")
def get_thread(thread_id: str) -> tuple[str, list]:
    """Read a whole conversation: every mail in it, oldest first.

    Use it to follow a back-and-forth or to read the latest reply. Older mails are shortened;
    open one with get_message to read it in full. Drafts are not included.

    Args:
        thread_id: The thread id from search_threads.
    """
    mails = read.thread(thread_id)
    if not mails:
        return "This conversation has no mail.", []
    return "\n\n---\n\n".join(mail_block(m) for m in mails), mails

@tool(parse_docstring=True, response_format="content_and_artifact")
def get_message(message_id: str) -> tuple[str, list]:
    """Read one mail in full: sender, recipients, date, subject, attachment names and text.

    Use it when you know the mail's id (from get_thread) and need its exact words.

    Args:
        message_id: The message id from get_thread.
    """
    mail = read.message(message_id)
    return mail_block(mail), [mail]

@tool(parse_docstring=True, response_format="content_and_artifact")
def list_labels() -> tuple[str, list]:
    """List the labels in the user's Gmail (their own labels and Gmail's, like INBOX or STARRED).

    Use it to find the name to search with, e.g. search_threads("label:receipts").
    """
    labels = read.labels()
    lines = [f"{label['name']}" + ("  (Gmail's own)" if label["type"] == "system" else "") for label in labels]
    return "\n".join(lines) or "No labels.", labels

@tool(parse_docstring=True, response_format="content_and_artifact")
def list_drafts(query: str = "", max_results: int = 20) -> tuple[str, list]:
    """List the user's saved drafts (mails written but not sent), newest first.

    Args:
        query: Gmail search words to filter the drafts, e.g. "to:sam@example.com". Use "" for all.
        max_results: How many drafts to return (1 to 50).
    """
    drafts = read.drafts(query, max_results=min(max(max_results, 1), 50))
    if not drafts:
        return "No drafts.", []
    lines = [
        f"{short_time(d)}  To: {d['to'] or '(nobody yet)'}  “{d['subject'] or '(no subject)'}”  {d['snippet'][:SNIPPET_CHARS]}  [draft: {d['draft_id']}]"
        for d in drafts
    ]
    return "\n".join(lines), drafts

@tool(parse_docstring=True, response_format="content_and_artifact")
def get_draft(draft_id: str) -> tuple[str, list]:
    """Read one saved draft in full.

    Args:
        draft_id: The draft id from list_drafts.
    """
    mail = read.draft(draft_id)
    return mail_block(mail, id_name="draft"), [mail]

GMAIL_TOOLS = [search_threads, get_thread, get_message, list_labels, list_drafts, get_draft]
