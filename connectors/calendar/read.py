import re
from datetime import date, datetime, time, timedelta

from connectors.calendar.client import get_service

MAX_DESCRIPTION_CHARS = 1000

def day_start(day):
    # "2026-11-16" becomes midnight of that day in the laptop's time zone
    return datetime.combine(date.fromisoformat(day), time()).astimezone().isoformat()

def calendars():
    # the calendars shown in the user's Google Calendar list
    found = get_service().calendarList().list().execute()
    return [
        {
            "id": item["id"],
            "name": item.get("summaryOverride") or item.get("summary", ""),
            "primary": item.get("primary", False),
            "access": item.get("accessRole", ""),
        }
        for item in found.get("items", [])
    ]

def summary(event):
    start, finish = event.get("start", {}), event.get("end", {})
    return {
        "id": event["id"],
        "title": event.get("summary", ""),
        # all-day events have a "date", timed events a "dateTime"
        "start": start.get("dateTime") or start.get("date", ""),
        "end": finish.get("dateTime") or finish.get("date", ""),
        "all_day": "date" in start,
        "location": event.get("location", ""),
        "description": event.get("description", "")[:MAX_DESCRIPTION_CHARS],
        "link": event.get("htmlLink", ""),
    }

MAX_PAGES = 10

def squash(text):
    # "CS 249" and "cs-249" both become "cs249"
    return re.sub(r"[\W_]+", "", text.lower())

def matches(event, query):
    text = squash(f"{event.get('summary', '')} {event.get('location', '')} {event.get('description', '')}")
    return all(squash(word) in text for word in query.split())

def fetch(calendar_id, start_day, end_day, query, max_results):
    # every event from the start of start_day to the end of end_day, a page at a time
    end = (date.fromisoformat(end_day) + timedelta(days=1)).isoformat()
    items, page = [], None
    for _ in range(MAX_PAGES):
        found = get_service().events().list(
            calendarId=calendar_id,
            timeMin=day_start(start_day),
            timeMax=day_start(end),
            q=query or None,
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
            pageToken=page,
        ).execute()
        items += found.get("items", [])
        page = found.get("nextPageToken")
        if not page or (not query and len(items) >= max_results):
            break
    return items

def events(start_day, end_day, query="", max_results=25, calendar_id="primary"):
    items = fetch(calendar_id, start_day, end_day, query, max_results)
    if query and not items:
        # Google's search needs the exact words ("CS 249" misses "CS249"), so look again more loosely
        items = [e for e in fetch(calendar_id, start_day, end_day, "", 250 * MAX_PAGES) if matches(e, query)]
    return [summary(event) for event in items[:max_results]]

def event(event_id, calendar_id="primary"):
    # one event in full: who is coming, who organized it, the video call link
    item = get_service().events().get(calendarId=calendar_id, eventId=event_id).execute()
    return summary(item) | {
        "description": item.get("description", ""),
        "organizer": item.get("organizer", {}).get("email", ""),
        "attendees": [
            {"email": a.get("email", ""), "name": a.get("displayName", ""), "response": a.get("responseStatus", "")}
            for a in item.get("attendees", [])
        ],
        "video_call": item.get("hangoutLink", ""),
        "repeats": bool(item.get("recurringEventId") or item.get("recurrence")),
        "status": item.get("status", ""),
    }

if __name__ == "__main__":
    today = date.today()
    for event in events(today.isoformat(), (today + timedelta(days=7)).isoformat()):
        print(event["start"], event["title"] or "(no title)")
