import { getJson } from "./api.js";
import { $, button, el, toast } from "./dom.js";
import { closeDrawers } from "./panel.js";
import { state } from "./state.js";

// app id -> the name shown, filled from the server's list
export const APP_NAMES = {};

const WORDS = {
  checking: { state: "Checking", action: "" },
  connected: { state: "Connected", action: "Disconnect" },
  not_connected: { state: "Not connected", action: "Connect" },
  connecting: { state: "Connecting", action: "Connect" },
};

const isOn = (value) => value === "connected";

// a plain drawing for each app (not the company's logo), so no two rows look alike
const MARKS = {
  gmail: '<path d="M4 6.5h16v11H4z"/><path d="M4 7l8 6 8-6"/>',
  calendar: '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
  files: '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
  github: '<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/>',
  slack: '<path d="M9.5 4l-2 16M16.5 4l-2 16M4.5 9h16M3.5 15h16"/>',
};

function drawMark(mark, name) {
  const app = mark.dataset.app;
  if (MARKS[app]) mark.innerHTML = `<svg viewBox="0 0 24 24">${MARKS[app]}</svg>`;
  else mark.textContent = name.slice(0, 1).toUpperCase();
}

export function showApps(apps) {
  state.apps = { ...state.apps, ...apps };
  Object.entries(state.apps).forEach(([name, value]) => showApp(name, value));
  showSummary();
  showHints();
  showView($("connectors").dataset.view);
}

// one row in the Connectors popup
function showApp(name, value) {
  const words = WORDS[value];
  if (!$(`connector-${name}`)) return;
  $(`connector-${name}`).dataset.state = value;
  $(`${name}-state`).textContent = words.state;
  const action = $(`${name}-action`);
  action.textContent = value === "connecting" ? "Signing in" : words.action;
  action.hidden = !words.action;
  action.disabled = value === "connecting";
  action.dataset.kind = value === "connected" ? "quiet" : "main";
}

// the small light and words on the Connectors button
function showSummary() {
  // just the light: green when something is connected, pulsing while signing in
  const values = Object.values(state.apps);
  const on = Object.keys(state.apps).filter((name) => isOn(state.apps[name]));
  let light = "not_connected";
  if (values.includes("checking")) light = "checking";
  else if (values.includes("connecting")) light = "connecting";
  else if (on.length) light = "connected";

  const summary = $("connectors-summary");
  summary.dataset.state = light;
  // the names, for the tooltip and screen readers
  const label = on.length ? `Connected: ${on.map((name) => APP_NAMES[name]).join(", ")}` : "Nothing connected yet";
  summary.title = label;
  summary.setAttribute("aria-label", label);
}

function showHints() {
  const { gmail, calendar, files } = state.apps;
  const things = [];
  if (isOn(gmail)) things.push("mail");
  if (isOn(calendar)) things.push("calendar");
  if (isOn(files)) things.push("files");
  // "mail, calendar or files"
  const list = things.length > 1 ? `${things.slice(0, -1).join(", ")} or ${things.at(-1)}` : things[0];
  $("input").placeholder = things.length ? `Ask about your ${list}, or anything` : "Ask me anything";

  const checking = Object.values(state.apps).includes("checking");
  $("connect-callout").hidden = checking || Object.values(state.apps).some(isOn);
}

// the Connectors window: a group ("Google", "On this laptop", "Other apps") and a row per app
export function addRows(rows) {
  const groups = $("connector-groups");
  for (const row of rows) {
    if ($(`connector-${row.id}`)) continue;
    APP_NAMES[row.id] = row.name;
    state.apps[row.id] = state.apps[row.id] || "checking";
    groupList(groups, row.group).append(appRow(row));
  }
}

function groupList(groups, name) {
  // the list for one group, made the first time it is needed
  let section = [...groups.children].find((child) => child.dataset.group === name);
  if (!section) {
    section = el("section", "connector-group");
    section.dataset.group = name;
    section.append(el("h3", null, name), el("ul", "connector-list"));
    groups.append(section);
  }
  return section.querySelector(".connector-list");
}

function appRow(app) {
  const row = el("li", "connector");
  row.id = `connector-${app.id}`;
  row.dataset.state = "checking";
  const mark = el("span", "connector-mark");
  mark.dataset.app = app.id;
  mark.setAttribute("aria-hidden", "true");
  drawMark(mark, app.name);
  const title = el("span", "connector-title");
  const status = el("span", "connector-state");
  status.id = `${app.id}-state`;
  title.append(el("span", "connector-name", app.name), status);
  const text = el("div", "connector-text");
  text.append(title, el("span", "connector-about", app.about));
  const toggle = button("connector-button", "", () => toggleApp(app.id));
  toggle.id = `${app.id}-action`;
  row.append(mark, text, toggle);
  return row;
}

// The window has two views: "mine" lists the connected apps; "add" lists the rest to connect.
const VIEWS = {
  mine: {
    title: "Connectors",
    intro: "Apps I can use when I answer. Reading happens right away; anything that changes something asks you first.",
    empty: "No apps connected yet. Add one so I can read your mail, events or files.",
  },
  add: {
    title: "Add a connector",
    intro: "Each app asks only for what it needs, and you can disconnect it any time.",
    empty: "Every app is already connected.",
  },
};

export function showView(view) {
  const dialog = $("connectors");
  dialog.dataset.view = view;
  const words = VIEWS[view];
  $("connectors-title").textContent = words.title;
  $("connectors-intro").textContent = words.intro;
  const shown = Object.values(state.apps).filter((value) => (view === "mine") === isOn(value));
  $("connectors-empty").textContent = words.empty;
  $("connectors-empty").hidden = shown.length > 0 || Object.values(state.apps).includes("checking");
  $("connectors-add").hidden = view === "add" || !Object.values(state.apps).some((value) => !isOn(value));
}

export function openConnectors() {
  closeDrawers();
  // with nothing connected yet, go straight to the list of apps to add
  showView(Object.values(state.apps).some(isOn) ? "mine" : "add");
  $("connectors").showModal();
}

$("connectors-add").addEventListener("click", () => showView("add"));
$("connectors-back").addEventListener("click", () => showView("mine"));

export async function toggleApp(name) {
  const label = APP_NAMES[name];
  if (state.apps[name] === "connected") {
    showApps((await getJson(`/api/connectors/${name}/disconnect`, { method: "POST" })).apps);
    toast(`${label} disconnected`);
    return;
  }
  showApps({ [name]: "connecting" });
  try {
    showApps((await getJson(`/api/connectors/${name}/connect`, { method: "POST" })).apps);
    toast(`${label} connected`);
    // back to the connected apps, where the new one now shows
    if ($("connectors").open) showView("mine");
  } catch (error) {
    showApps({ [name]: "not_connected" });
    toast(`Couldn't connect ${label}: ${error.message}`);
  }
}
