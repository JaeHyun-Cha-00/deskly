from datetime import date, datetime, timedelta

from connectors.calendar.client import get_service
from connectors.calendar.read import summary

def when(text):
    # "2026-11-17" is an all-day date; "2026-11-17T15:00" is a time on the laptop's clock
    if len(text) == 10:
        return {"date": date.fromisoformat(text).isoformat()}
    return {"dateTime": datetime.fromisoformat(text).astimezone().isoformat()}

def create_event(title, start, end, location="", description="", calendar_id="primary"):
    start_at, end_at = when(start), when(end)
    if ("date" in start_at) != ("date" in end_at):
        raise ValueError("Start and end must both be days (YYYY-MM-DD) or both be times (YYYY-MM-DDTHH:MM).")
    if "date" in end_at:
        # Google's all-day end day is not included, so "Nov 17 to Nov 17" ends on Nov 18
        end_at = {"date": (date.fromisoformat(end) + timedelta(days=1)).isoformat()}
    first = start_at.get("date") or start_at["dateTime"]
    last = end_at.get("date") or end_at["dateTime"]
    if last <= first:
        raise ValueError("The event must end after it starts.")

    body = {"summary": title, "location": location, "description": description, "start": start_at, "end": end_at}
    created = get_service().events().insert(calendarId=calendar_id, body=body).execute()
    return summary(created)
