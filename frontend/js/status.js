import { getJson } from "./api.js";
import { showTitle } from "./chats.js";
import { addRows, showApps } from "./connectors.js";
import { $, sendButton, store } from "./dom.js";
import { state } from "./state.js";

export function applyTheme(theme) {
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
  store("theme", theme);
}

// how see-through the desktop window is; a browser tab always stays solid
export function applySeeThrough(settings) {
  const root = document.documentElement.style;
  root.setProperty("--bg-op", `${state.desktop ? settings.background : 100}%`);
  root.setProperty("--text-op", `${state.desktop ? settings.text : 100}%`);
}

export async function loadStatus() {
  try {
    const status = await getJson("/api/status");
    state.offline = false;
    state.modelKey = status.model_key;
    state.desktop = status.desktop;
    state.settings = status.settings;
    state.appName = status.app_name;
    $("brand").textContent = status.app_name;
    applyTheme(state.settings.theme);
    applySeeThrough(state.settings);
    addRows(status.connectors || []);
    showApps(status.apps);
  } catch {
    state.offline = true;
  }
  showTitle();
  showNotice();
}

export function showNotice() {
  const notice = $("notice");
  const action = $("notice-action");
  let text = "";
  action.hidden = true;
  if (state.offline) {
    text = "Can't reach the app. If you closed the terminal, start it again with: uv run python -m assistant.web";
    action.textContent = "Try again";
    action.hidden = false;
  } else if (!state.modelKey) {
    text = "Add your OpenRouter API key to .env as OPENROUTER_API_KEY, then restart the app.";
  }
  notice.hidden = !text;
  $("notice-text").textContent = text;
  sendButton.disabled = !state.busy && (state.offline || !state.modelKey);
}

