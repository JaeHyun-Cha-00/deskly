import { getJson, sendJson } from "./api.js";
import { $, button, el, toast } from "./dom.js";
import { closeDrawers } from "./panel.js";
import { state } from "./state.js";

// app id -> the name shown, filled from the server's list
const APP_NAMES = {};
// app id -> whether its tools can be chosen (MCP servers)
const HAS_TOOLS = {};

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
  notion: '<path d="M6.5 3.5h8l4 4v13h-12z"/><path d="M14.5 3.5v4h4M9.5 11.5h6M9.5 15h6"/>',
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
    HAS_TOOLS[row.id] = row.tools;
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
  if (app.tools) {
    // only shown once the app is connected (CSS)
    const tools = button("connector-tools", "Choose tools", () => openTools(app.id));
    text.append(tools);
  }
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
  tools: {
    title: "Tools",
    intro: "Turn on only what you need. Every tool that is on is sent to the model with each question, so fewer tools make answers faster, cheaper and more accurate. Tools that change something always ask you first.",
    empty: "",
  },
};

function showView(view) {
  const dialog = $("connectors");
  dialog.dataset.view = view;
  const words = VIEWS[view];
  $("connectors-title").textContent = view === "tools" ? `${APP_NAMES[picking.app]} tools` : words.title;
  $("connectors-intro").textContent = words.intro;
  const shown = Object.values(state.apps).filter((value) => (view === "mine") === isOn(value));
  $("connectors-empty").textContent = words.empty;
  $("connectors-empty").hidden = view === "tools" || shown.length > 0 || Object.values(state.apps).includes("checking");
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

async function toggleApp(name) {
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
    // an MCP app goes straight to choosing its tools; others back to the connected apps
    if ($("connectors").open) {
      if (HAS_TOOLS[name]) openTools(name);
      else showView("mine");
    }
  } catch (error) {
    showApps({ [name]: "not_connected" });
    toast(`Couldn't connect ${label}: ${error.message}`);
  }
}

// The Tools view: every tool one MCP app offers, on or off, with what each costs per question.
const picking = { app: "", tools: [] };

const thousands = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n));

async function openTools(app) {
  picking.app = app;
  picking.tools = [];
  showView("tools");
  const picker = $("tool-picker");
  picker.replaceChildren(el("p", "connectors-empty", "Getting the tools…"));
  $("tools-total").textContent = "";
  try {
    picking.tools = (await getJson(`/api/connectors/${app}/tools`)).tools;
  } catch (error) {
    picker.replaceChildren(el("p", "connectors-empty", `Couldn't get the tools: ${error.message}`));
    return;
  }
  if (picking.app !== app) return;
  showTools();
}

function showTools() {
  const picker = $("tool-picker");
  picker.replaceChildren();
  const groups = [["Reads", false], ["Changes something (asks you first)", true]];
  for (const [heading, write] of groups) {
    const tools = picking.tools.filter((tool) => tool.write === write);
    if (!tools.length) continue;
    const section = el("section", "tool-group");
    section.append(el("h3", null, `${heading} · ${tools.length}`));
    for (const tool of tools) {
      const row = el("label", "tool-row");
      const box = el("input");
      box.type = "checkbox";
      box.checked = tool.on;
      box.addEventListener("change", () => {
        tool.on = box.checked;
        showTotal();
      });
      const text = el("span", "tool-text");
      text.append(el("span", "tool-name", tool.title), el("span", "tool-about", tool.about));
      row.append(box, text, el("span", "tool-cost", thousands(tool.tokens)));
      section.append(row);
    }
    picker.append(section);
  }
  showTotal();
}

function showTotal() {
  const on = picking.tools.filter((tool) => tool.on);
  const tokens = on.reduce((sum, tool) => sum + tool.tokens, 0);
  const total = $("tools-total");
  total.textContent = `${on.length} of ${picking.tools.length} on · about ${thousands(tokens)} tokens with every question`;
  // past this, the tools alone take a big part of what the model can hold
  total.dataset.level = tokens > 30000 ? "full" : tokens > 15000 ? "high" : "ok";
}

$("tools-reset").addEventListener("click", () => {
  picking.tools.forEach((tool) => { tool.on = tool.recommended; });
  showTools();
});

$("tools-save").addEventListener("click", async () => {
  const names = picking.tools.filter((tool) => tool.on).map((tool) => tool.name);
  try {
    await sendJson(`/api/connectors/${picking.app}/tools`, "PUT", { tools: names });
  } catch (error) {
    toast(`Couldn't save: ${error.message}`);
    return;
  }
  toast(`${APP_NAMES[picking.app]}: ${names.length} tools on`);
  showView("mine");
});
