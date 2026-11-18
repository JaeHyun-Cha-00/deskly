import { getJson, sendJson } from "./api.js";
import { shortDate } from "./dates.js";
import { $, button, el, toast } from "./dom.js";
import { closeDrawers } from "./panel.js";

// what the agent remembers about the user: the Memory button and window
let memory = { on: true, facts: [], max: 50 };

function showCount() {
  $("memory-count").textContent = memory.on ? (memory.facts.length || "") : "Off";
}

export async function loadMemory() {
  try {
    memory = await getJson("/api/memory");
  } catch {
    return;
  }
  showCount();
  if ($("memory").open) showList();
}

export async function openMemory() {
  closeDrawers();
  await loadMemory();
  showList();
  $("memory").showModal();
}

async function change(path, method, data) {
  try {
    memory = await sendJson(path, method, data);
  } catch (error) {
    toast(`Couldn't change memory: ${error.message}`);
    return false;
  }
  showCount();
  showList();
  return true;
}

function showList() {
  $("memory-on").checked = memory.on;
  $("memory-empty").hidden = memory.facts.length > 0;
  $("memory-limit").textContent = `${memory.facts.length} of ${memory.max}`;
  resetClear();
  const list = $("memory-list");
  list.replaceChildren();
  // newest first
  for (const fact of [...memory.facts].reverse()) list.append(factRow(fact));
}

function factRow(fact) {
  const row = el("li", "memory-fact");
  const text = el("div", "memory-text");
  text.append(el("span", "memory-sentence", fact.text), el("span", "memory-when", `Saved ${shortDate(fact.at)}`));
  const actions = el("div", "memory-actions");
  actions.append(
    button("quiet-button", "Edit", () => startEdit(row, fact)),
    button("quiet-button danger", "Delete", async () => {
      if (await change(`/api/memory/${fact.id}`, "DELETE")) toast("Forgotten");
    }),
  );
  row.append(text, actions);
  return row;
}

function startEdit(row, fact) {
  const field = el("input", "memory-field");
  field.value = fact.text;
  field.maxLength = 200;
  field.setAttribute("aria-label", "Edit this memory");
  const save = async () => {
    const text = field.value.trim();
    if (text === fact.text) return showList();
    if (await change(`/api/memory/${fact.id}`, "PUT", { text })) toast("Saved");
  };
  field.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); save(); }
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); showList(); }
  });
  const actions = el("div", "memory-actions");
  actions.append(button("quiet-button", "Save", save), button("quiet-button", "Cancel", showList));
  row.replaceChildren(field, actions);
  field.focus();
}

function resetClear() {
  const clear = $("memory-clear");
  delete clear.dataset.confirm;
  clear.textContent = "Delete all";
  clear.disabled = !memory.facts.length;
}

$("memory-clear").addEventListener("click", async () => {
  const clear = $("memory-clear");
  // two clicks, like deleting all chats
  if (!("confirm" in clear.dataset)) {
    clear.dataset.confirm = "";
    clear.textContent = `Delete ${memory.facts.length} memor${memory.facts.length === 1 ? "y" : "ies"}`;
    return;
  }
  if (await change("/api/memory", "DELETE")) toast("Memory cleared");
});
$("memory-clear").addEventListener("blur", resetClear);

$("memory-on").addEventListener("change", async (event) => {
  if (await change("/api/memory/on", "PUT", { on: event.target.checked })) toast(memory.on ? "Memory on" : "Memory off");
});
$("open-memory").addEventListener("click", openMemory);
$("close-memory").addEventListener("click", () => $("memory").close());
