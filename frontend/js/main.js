import { loadChats, newChat, showChat, startRename } from "./chats.js";
import { APP_NAMES, openConnectors, toggleApp } from "./connectors.js";
import { $, IS_MAC, MOD, WIDE, app, input, isTyping, palette } from "./dom.js";
import { openPalette } from "./palette.js";
import { closeDrawers, panelIsOpen, setPanel, showPanel, updateScrim } from "./panel.js";
import { openSettings } from "./settings.js";
import { state } from "./state.js";
import { loadStatus } from "./status.js";

$("new-chat").addEventListener("click", newChat);
$("open-palette").addEventListener("click", openPalette);
$("open-settings").addEventListener("click", openSettings);
$("callout-connectors").addEventListener("click", openConnectors);
$("open-connectors").addEventListener("click", openConnectors);
$("close-connectors").addEventListener("click", () => $("connectors").close());
Object.keys(APP_NAMES).forEach((name) => $(`${name}-action`).addEventListener("click", () => toggleApp(name)));
$("chat-title").addEventListener("click", startRename);
$("toggle-panel").addEventListener("click", () => setPanel(!panelIsOpen()));
$("panel-close").addEventListener("click", () => setPanel(false));
$("panel-back").addEventListener("click", () => showPanel(state.panel.back || { view: "sources" }));
$("open-rail").addEventListener("click", () => {
  app.dataset.rail = "open";
  updateScrim();
  // after the drawer becomes visible
  setTimeout(() => $("new-chat").focus(), 50);
});
$("notice-action").addEventListener("click", loadStatus);
window.addEventListener("resize", updateScrim);
window.addEventListener("focus", () => { if (!state.busy) loadStatus(); });
$("close-rail").addEventListener("click", closeDrawers);
$("scrim").addEventListener("click", closeDrawers);

document.addEventListener("keydown", (event) => {
  const mod = IS_MAC ? event.metaKey : event.ctrlKey;
  const key = event.key.toLowerCase();
  const dialogOpen = document.querySelector("dialog[open]");

  if (mod && key === "k") {
    event.preventDefault();
    if (palette.open) palette.close();
    else if (!dialogOpen) openPalette();
  } else if (mod && key === "b" && !dialogOpen) {
    event.preventDefault();
    setPanel(!panelIsOpen());
  } else if (event.key === "/" && !dialogOpen && !isTyping(event.target)) {
    event.preventDefault();
    input.focus();
  } else if (event.key === "Escape" && !dialogOpen && !event.defaultPrevented) {
    if (app.dataset.rail === "open" || (!WIDE.matches && panelIsOpen())) closeDrawers();
    else if (state.panel.view === "mail" && panelIsOpen()) showPanel(state.panel.back || { view: "sources" });
  }
});

WIDE.addEventListener("change", () => {
  setPanel(WIDE.matches && panelIsOpen());
});

document.querySelectorAll("kbd[data-mod]").forEach((kbd) => { kbd.textContent = `${MOD} ${kbd.textContent}`; });
$("today").textContent = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
setPanel(false);
showChat(state.chatId, "", []);
loadStatus();
loadChats().catch(() => {});
input.focus();
