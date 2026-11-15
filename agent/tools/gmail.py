import json

from langchain.tools import tool

from connectors.gmail import read

@tool(parse_docstring=True)
def search_emails(query: str, max_results: int = 10) -> str:
    """Search the user's Gmail and list the matching mails, newest first.

    Uses Gmail search words, e.g. "is:unread newer_than:1d", "from:alice@example.com",
    "subject:invoice", "has:attachment after:2026/11/01". An empty query lists the newest mail.
    Returns each mail's id, sender, subject, date, a short snippet, and whether it is unread.

    Args:
        query: Gmail search words. Use "" for the newest mail.
        max_results: How many mails to return (1 to 25).
    """
    mails = read.search(query, max_results=min(max(max_results, 1), 25))
    if not mails:
        return "No mail matched."
    return json.dumps(mails, ensure_ascii=False, indent=1)

@tool(parse_docstring=True)
def read_email(email_id: str) -> str:
    """Read one mail in full: sender, recipients, subject, date and body text.

    Args:
        email_id: The id from search_emails.
    """
    return json.dumps(read.read(email_id), ensure_ascii=False, indent=1)

GMAIL_TOOLS = [search_emails, read_email]
