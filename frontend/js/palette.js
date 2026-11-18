import { newChat, openChat } from "./chats.js";
import { openConnectors } from "./connectors.js";
import { shortDate } from "./dates.js";
import { $, MOD, el, palette, paletteInput, paletteList, settingsDialog } from "./dom.js";
import { panelIsOpen, setPanel } from "./panel.js";
import { changeSetting, openSettings } from "./settings.js";
import { state } from "./state.js";

let paletteItems = [];
let paletteActive = 0;

function paletteCommands() {
  const themes = { system: "Match system", light: "Light", dark: "Dark" };
  const items = [
    { group: "Actions", label: "New chat", run: newChat },
    { group: "Actions", label: panelIsOpen() ? "Hide sources" : "Show sources", hint: `${MOD} B`, run: () => setPanel(!panelIsOpen()) },
    { group: "Actions", label: "Open settings", run: openSettings },
    ...Object.entries(themes).map(([value, name]) => ({ group: "Actions", label: `Theme: ${name}`, run: () => changeSetting("theme", value) })),
  ];
  items.splice(3, 0, { group: "Actions", label: "Open connectors", run: openConnectors });
  for (const chat of state.chats) {
    items.push({ group: "Chats", label: chat.title || "Untitled chat", hint: shortDate(chat.updated), run: () => openChat(chat.id) });
  }
  return items;
}

export function openPalette() {
  paletteInput.value = "";
  filterPalette();
  palette.showModal();
  paletteInput.focus();
}

function filterPalette() {
  const words = paletteInput.value.toLowerCase().split(/\s+/).filter(Boolean);
  paletteItems = paletteCommands().filter((item) => words.every((word) => item.label.toLowerCase().includes(word)));
  paletteActive = 0;

  paletteList.replaceChildren();
  if (!paletteItems.length) paletteList.append(el("li", "palette-empty", "Nothing matches."));
  let group = null;
  paletteItems.forEach((item, index) => {
    if (item.group !== group) {
      group = item.group;
      const heading = el("li", "palette-group", group);
      heading.setAttribute("role", "presentation");
      paletteList.append(heading);
    }
    const option = el("li", "palette-item");
    option.id = `palette-item-${index}`;
    option.setAttribute("role", "option");
    option.append(el("span", "palette-label", item.label));
    if (item.hint) option.append(el("span", "palette-hint", item.hint));
    option.addEventListener("mousemove", () => { if (paletteActive !== index) markPalette(index); });
    option.addEventListener("click", () => runPalette(index));
    paletteList.append(option);
  });
  markPalette(0);
}

function markPalette(index) {
  paletteActive = index;
  paletteList.querySelectorAll(".palette-item").forEach((option) => {
    const selected = option.id === `palette-item-${index}`;
    option.setAttribute("aria-selected", String(selected));
    if (selected) option.scrollIntoView({ block: "nearest" });
  });
  paletteInput.setAttribute("aria-activedescendant", `palette-item-${index}`);
}

function runPalette(index) {
  const item = paletteItems[index];
  if (!item) return;
  palette.close();
  item.run();
}

paletteInput.addEventListener("input", filterPalette);
paletteInput.addEventListener("keydown", (event) => {
  const count = paletteItems.length;
  if (event.key === "ArrowDown" && count) { event.preventDefault(); markPalette((paletteActive + 1) % count); }
  if (event.key === "ArrowUp" && count) { event.preventDefault(); markPalette((paletteActive - 1 + count) % count); }
  if (event.key === "Enter") { event.preventDefault(); runPalette(paletteActive); }
});

for (const dialog of [palette, settingsDialog, $("connectors")]) {
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
}
