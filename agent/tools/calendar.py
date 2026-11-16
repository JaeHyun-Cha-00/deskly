import re
from datetime import date, datetime

from langchain.tools import tool

from connectors.calendar import read, write

MAX_DESCRIPTION_CHARS = 200

def when(event):
    # "Tue Nov 17 12:00-13:30", or "Tue Nov 17, all day"
    if event["all_day"]:
        return f"{date.fromisoformat(event['start']):%a %b %-d}, all day"
    start = datetime.fromisoformat(event["start"]).astimezone()
    end = datetime.fromisoformat(event["end"]).astimezone()
    end_text = f"{end:%H:%M}" if end.date() == start.date() else f"{end:%a %b %-d %H:%M}"
    return f"{start:%a %b %-d %H:%M}-{end_text}"

def event_line(event):
    # one short line per event, e.g. "Tue Nov 17 12:00-13:30  CS201  at Room 2  [id: abc]"
    parts = [when(event), event["title"] or "(no title)"]
    if event["location"]:
        parts.append(f"at {event['location']}")
    description = re.sub(r"\s+", " ", event["description"]).strip()
    if description:
        parts.append(f"({description[:MAX_DESCRIPTION_CHARS]})")
    # the id lets the model open the event with get_event
    parts.append(f"[id: {event['id']}]")
    return "  ".join(parts)

# The model reads the short text; the screen gets the full events (the "artifact").

@tool(parse_docstring=True, response_format="content_and_artifact")
def list_calendars() -> tuple[str, list]:
    """List the calendars in the user's Google Calendar (their own and the ones they subscribe to).

    Use it to find a calendar's id when the user names one, e.g. "my school calendar" or
    "holidays". Most questions are about the primary calendar and don't need this.
    """
    calendars = read.calendars()
    lines = [
        f"{c['name']}  [id: {c['id']}]" + ("  (primary)" if c["primary"] else "") + ("  (read only)" if c["access"] == "reader" else "")
        for c in calendars
    ]
    return "\n".join(lines) or "No calendars.", calendars

@tool(parse_docstring=True, response_format="content_and_artifact")
def list_events(start_day: str, end_day: str, query: str = "", calendar_id: str = "primary", max_results: int = 100) -> tuple[str, list]:
    """List the events on the user's Google Calendar between two days, earliest first.

    Use it for "what's on today", "my week", and to find an event ("when is my midterm"):
    give a query and a wide range of days. Free time is the gaps between the events.
    Returns one line per event: day, start-end time (24-hour, the user's time zone), title,
    location, a short description and the event's id.

    Args:
        start_day: The first day, as YYYY-MM-DD.
        end_day: The last day (included), as YYYY-MM-DD.
        query: Words to look for in the events, e.g. "midterm". Use "" for every event.
        calendar_id: Which calendar, from list_calendars. Use "primary" for the user's own calendar.
        max_results: How many events to return (1 to 250).
    """
    max_results = min(max(max_results, 1), 250)
    events = read.events(start_day, end_day, query, max_results=max_results, calendar_id=calendar_id)
    if not events:
        return "No events in that range.", []
    lines = [event_line(e) for e in events]
    if len(events) == max_results:
        lines.append(f"(Stopped at {max_results} events; there may be more. Ask for fewer days.)")
    return "\n".join(lines), events

@tool(parse_docstring=True, response_format="content_and_artifact")
def get_event(event_id: str, calendar_id: str = "primary") -> tuple[str, list]:
    """Open one event in full: its whole description, organizer, attendees and their answers,
    video call link, and whether it repeats.

    Use it when the user asks for details that list_events doesn't show, e.g. who is coming.

    Args:
        event_id: The id from list_events.
        calendar_id: The calendar the event is on. Use "primary" for the user's own calendar.
    """
    event = read.event(event_id, calendar_id)
    lines = [f"{event['title'] or '(no title)'}", when(event)]
    if event["location"]:
        lines.append(f"Location: {event['location']}")
    if event["organizer"]:
        lines.append(f"Organizer: {event['organizer']}")
    for person in event["attendees"]:
        lines.append(f"Attendee: {person['name'] or person['email']} ({person['response']})")
    if event["video_call"]:
        lines.append(f"Video call: {event['video_call']}")
    if event["repeats"]:
        lines.append("Repeats: yes")
    if event["status"] == "cancelled":
        lines.append("Status: cancelled")
    description = event["description"].strip()
    if description:
        lines.append(f"Description: {description}")
    return "\n".join(lines), [event]

@tool(parse_docstring=True, response_format="content_and_artifact")
def create_event(title: str, start: str, end: str, location: str = "", description: str = "", calendar_id: str = "primary") -> tuple[str, list]:
    """Add an event to the user's Google Calendar. The user sees it and must approve it first.

    Times are on the user's clock. For an all-day event give days only.

    Args:
        title: The event's name, e.g. "Dentist".
        start: When it starts: "YYYY-MM-DDTHH:MM", or "YYYY-MM-DD" for an all-day event.
        end: When it ends, in the same form as start. For all-day events, the last day.
        location: Where, if the user said.
        description: Notes for the event, if any.
        calendar_id: Which calendar, from list_calendars. Use "primary" for the user's own calendar.
    """
    event = write.create_event(title, start, end, location, description, calendar_id)
    return f"Added: {when(event)}  {event['title']}  [id: {event['id']}]", [event]

CALENDAR_TOOLS = [list_calendars, list_events, get_event, create_event]

# tools that change something; each call waits for the user's approval
CALENDAR_WRITE_TOOLS = {"create_event"}
