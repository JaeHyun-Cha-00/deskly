import { api, sendJson } from "./api.js";
import { loadChats, showChat } from "./chats.js";
import { $, settingsDialog, toast } from "./dom.js";
import { closeDrawers } from "./panel.js";
import { state } from "./state.js";
import { applyTheme } from "./status.js";

export function openSettings() {
  closeDrawers();
  for (const name of ["theme", "length"]) {
    document.querySelectorAll(`input[name="${name}"]`).forEach((radio) => { radio.checked = radio.value === state.settings[name]; });
  }
  resetDeleteAll();
  settingsDialog.showModal();
}

export async function changeSetting(key, value) {
  try {
    state.settings = await sendJson("/api/settings", "PUT", { [key]: value });
    applyTheme(state.settings.theme);
    toast("Saved");
  } catch (error) {
    toast(`Couldn't save: ${error.message}`);
  }
}

$("settings-form").addEventListener("change", (event) => {
  if (event.target.name) changeSetting(event.target.name, event.target.value);
});

export function resetDeleteAll() {
  const remove = $("delete-all");
  delete remove.dataset.confirm;
  remove.textContent = "Delete all chats";
  remove.disabled = !state.chats.length;
}

$("delete-all").addEventListener("click", async () => {
  const remove = $("delete-all");
  if (!("confirm" in remove.dataset)) {
    remove.dataset.confirm = "";
    remove.textContent = `Delete ${state.chats.length} chat${state.chats.length === 1 ? "" : "s"}`;
    return;
  }
  await api("/api/chats", { method: "DELETE" });
  if (!state.busy) showChat(crypto.randomUUID(), "", []);
  await loadChats();
  resetDeleteAll();
  toast("All chats deleted");
});

$("delete-all").addEventListener("blur", resetDeleteAll);
