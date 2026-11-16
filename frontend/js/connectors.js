import { getJson } from "./api.js";
import { $, button, el, toast } from "./dom.js";
import { closeDrawers } from "./panel.js";
import { state } from "./state.js";

export const APP_NAMES = { gmail: "Gmail", calendar: "Calendar", files: "Files" };

const WORDS = {
  checking: { state: "Checking", action: "" },
  connected: { state: "Connected", action: "Disconnect" },
  not_connected: { state: "Not connected", action: "Connect" },
  connecting: { state: "Connecting", action: "Connect" },
  demo: { state: "Demo mail", action: "" },
  not_in_demo: { state: "Not in demo mode", action: "" },
};

const isOn = (value) => value === "connected" || value === "demo";

export function showApps(apps) {
  state.apps = { ...state.apps, ...apps };
  Object.entries(state.apps).forEach(([name, value]) => showApp(name, value));
  showSummary();
  showHints();
}

// one row in the Connectors popup
function showApp(name, value) {
  const words = WORDS[value];
  $(`connector-${name}`).dataset.state = value;
  $(`${name}-state`).textContent = words.state;
  const action = $(`${name}-action`);
  action.textContent = words.action;
  action.hidden = !words.action;
  action.disabled = value === "connecting";
}

// the small light and words on the Connectors button
function showSummary() {
  const values = Object.values(state.apps);
  const on = Object.keys(state.apps).filter((name) => isOn(state.apps[name]));
  let light = "not_connected";
  let text = "None yet";
  if (values.includes("checking")) [light, text] = ["checking", ""];
  else if (values.includes("connecting")) [light, text] = ["connecting", "Signing in"];
  else if (values.includes("demo")) [light, text] = ["demo", "Demo mail"];
  else if (on.length) [light, text] = ["connected", on.map((name) => APP_NAMES[name]).join(", ")];

  const summary = $("connectors-summary");
  summary.dataset.state = light;
  summary.textContent = text;
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

  $("demo-badge").hidden = gmail !== "demo";
  $("demo-note").hidden = gmail !== "demo";
  const checking = Object.values(state.apps).includes("checking");
  $("connect-callout").hidden = checking || Object.values(state.apps).some(isOn);
}

// one Connectors row for each MCP server the app knows about
export function addServerRows(servers) {
  const list = document.querySelector(".connector-list");
  for (const server of servers) {
    if ($(`connector-${server.id}`)) continue;
    APP_NAMES[server.id] = server.name;
    state.apps[server.id] = state.apps[server.id] || "checking";

    const row = el("li", "connector");
    row.id = `connector-${server.id}`;
    row.dataset.state = "checking";
    const mark = el("span", "connector-mark", server.name.slice(0, 1).toUpperCase());
    mark.setAttribute("aria-hidden", "true");
    const text = el("div", "connector-text");
    text.append(el("span", "connector-name", server.name), el("span", "connector-about", server.about));
    const action = el("div", "connector-action");
    const status = el("span", "connector-state");
    status.id = `${server.id}-state`;
    const toggle = button("primary-button", "", () => toggleApp(server.id));
    toggle.id = `${server.id}-action`;
    action.append(status, toggle);
    row.append(mark, text, action);
    list.append(row);
  }
}

export function openConnectors() {
  closeDrawers();
  $("connectors").showModal();
}

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
  } catch (error) {
    showApps({ [name]: "not_connected" });
    toast(`Couldn't connect ${label}: ${error.message}`);
  }
}
