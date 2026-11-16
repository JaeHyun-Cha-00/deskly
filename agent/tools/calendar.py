import re
from datetime import date, datetime

from langchain.tools import tool

from connectors.calendar import read

MAX_DESCRIPTION_CHARS = 200

def event_line(event):
    # one short line per event, e.g. "Tue Nov 17 12:00-13:30  CS201  at Room 2"
    if event["all_day"]:
        when = f"{date.fromisoformat(event['start']):%a %b %-d}, all day"
    else:
        start = datetime.fromisoformat(event["start"]).astimezone()
        end = datetime.fromisoformat(event["end"]).astimezone()
        end_text = f"{end:%H:%M}" if end.date() == start.date() else f"{end:%a %b %-d %H:%M}"
        when = f"{start:%a %b %-d %H:%M}-{end_text}"

    parts = [when, event["title"] or "(no title)"]
    if event["location"]:
        parts.append(f"at {event['location']}")
    description = re.sub(r"\s+", " ", event["description"]).strip()
    if description:
        parts.append(f"({description[:MAX_DESCRIPTION_CHARS]})")
    return "  ".join(parts)

# the model reads the short lines; the screen gets the full events (the "artifact")
@tool(parse_docstring=True, response_format="content_and_artifact")
def list_events(start_day: str, end_day: str, query: str = "", max_results: int = 100) -> tuple[str, list]:
    """List the events on the user's Google Calendar between two days, earliest first.

    Use it for "what's on today", "my week", and to find an event ("when is my midterm"):
    give a query and a wide range of days. Free time is the gaps between the events.
    Returns one line per event: day, start-end time (24-hour, the user's time zone), title,
    location and description.

    Args:
        start_day: The first day, as YYYY-MM-DD.
        end_day: The last day (included), as YYYY-MM-DD.
        query: Words to look for in the events, e.g. "midterm". Use "" for every event.
        max_results: How many events to return (1 to 250).
    """
    events = read.events(start_day, end_day, query, max_results=min(max(max_results, 1), 250))
    if not events:
        return "No events in that range.", []
    lines = [event_line(e) for e in events]
    if len(events) == max_results:
        lines.append(f"(Stopped at {max_results} events; there may be more. Ask for fewer days.)")
    return "\n".join(lines), events

CALENDAR_TOOLS = [list_events]
