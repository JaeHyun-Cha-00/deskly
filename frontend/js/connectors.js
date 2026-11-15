import { getJson } from "./api.js";
import { $, toast } from "./dom.js";
import { closeDrawers } from "./panel.js";
import { state } from "./state.js";

export const GMAIL = {
  checking: { summary: "", state: "Checking", action: "" },
  connected: { summary: "Gmail", state: "Connected", action: "Disconnect" },
  not_connected: { summary: "None yet", state: "Not connected", action: "Connect" },
  connecting: { summary: "Signing in", state: "Waiting for Google", action: "Connect" },
  demo: { summary: "Demo mail", state: "Demo mail", action: "" },
};

export function showGmail(gmail) {
  state.gmail = gmail;
  const words = GMAIL[gmail];
  const summary = $("connectors-summary");
  summary.dataset.state = gmail;
  summary.textContent = words.summary;

  $("connector-gmail").dataset.state = gmail;
  $("gmail-state").textContent = words.state;
  const action = $("gmail-action");
  action.textContent = words.action;
  action.hidden = !words.action;
  action.disabled = gmail === "connecting";

  const mail = gmail === "connected" || gmail === "demo";
  $("input").placeholder = mail ? "Ask about your mail, or anything" : "Ask me anything";
  $("demo-badge").hidden = gmail !== "demo";
  $("demo-note").hidden = gmail !== "demo";
  $("connect-callout").hidden = gmail !== "not_connected" && gmail !== "connecting";
}

export function openConnectors() {
  closeDrawers();
  $("connectors").showModal();
}

export async function connectGmail() {
  showGmail("connecting");
  try {
    showGmail((await getJson("/api/gmail/connect", { method: "POST" })).gmail);
    toast("Gmail connected");
  } catch (error) {
    showGmail("not_connected");
    toast(`Couldn't connect Gmail: ${error.message}`);
  }
}

export async function disconnectGmail() {
  showGmail((await getJson("/api/gmail/disconnect", { method: "POST" })).gmail);
  toast("Gmail disconnected");
}
