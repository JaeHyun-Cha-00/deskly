from datetime import date, datetime, time, timedelta

from connectors.calendar.client import get_service

MAX_DESCRIPTION_CHARS = 1000

def day_start(day):
    # "2026-11-16" becomes midnight of that day in the laptop's time zone
    return datetime.combine(date.fromisoformat(day), time()).astimezone().isoformat()

def events(start_day, end_day, query="", max_results=25):
    # every event from the start of start_day to the end of end_day
    end = (date.fromisoformat(end_day) + timedelta(days=1)).isoformat()
    found = get_service().events().list(
        calendarId="primary",
        timeMin=day_start(start_day),
        timeMax=day_start(end),
        q=query or None,
        singleEvents=True,
        orderBy="startTime",
        maxResults=max_results,
    ).execute()

    results = []
    for event in found.get("items", []):
        start, finish = event.get("start", {}), event.get("end", {})
        results.append({
            "id": event["id"],
            "title": event.get("summary", ""),
            # all-day events have a "date", timed events a "dateTime"
            "start": start.get("dateTime") or start.get("date", ""),
            "end": finish.get("dateTime") or finish.get("date", ""),
            "all_day": "date" in start,
            "location": event.get("location", ""),
            "description": event.get("description", "")[:MAX_DESCRIPTION_CHARS],
            "link": event.get("htmlLink", ""),
        })
    return results

if __name__ == "__main__":
    today = date.today()
    for event in events(today.isoformat(), (today + timedelta(days=7)).isoformat()):
        print(event["start"], event["title"] or "(no title)")
