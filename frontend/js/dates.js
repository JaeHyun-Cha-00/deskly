export function parseDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function daysAgo(date) {
  const day = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  return Math.round((day(new Date()) - day(date)) / 86400000);
}

export function shortDate(value) {
  const date = parseDate(value);
  if (!date) return value || "";
  const days = daysAgo(date);
  if (days === 0) return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  if (days === 1) return "Yesterday";
  if (days < 7) return date.toLocaleDateString("en-US", { weekday: "short" });
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function longDate(value) {
  const date = parseDate(value);
  if (!date) return value || "";
  return date.toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

export function chatGroup(value) {
  const days = daysAgo(parseDate(value) || new Date());
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return "Previous 7 days";
  if (days < 30) return "Previous 30 days";
  return "Older";
}
