import { api, getJson, sendJson } from "./api.js";
import { chatGroup } from "./dates.js";
import { $, ICONS, button, el, emptyEl, input, messagesEl, toast } from "./dom.js";
import { closeDrawers, showPanel } from "./panel.js";
import { state } from "./state.js";
import { renderSavedTurn, scrollToEnd } from "./turns.js";

export async function loadChats() {
  state.chats = await getJson("/api/chats");
  renderChatList();
}

export function renderChatList() {
  const list = $("chat-list");
  list.replaceChildren();
  if (!state.chats.length) {
    list.append(el("p", "chat-list-empty", "Your chats are saved here."));
    return;
  }

  let group = null;
  let items = null;
  for (const chat of state.chats) {
    if (chatGroup(chat.updated) !== group) {
      group = chatGroup(chat.updated);
      items = el("ul", "chat-items");
      list.append(el("h3", "chat-group", group), items);
    }
    const title = chat.title || "Untitled chat";
    const item = el("li", "chat-item");
    const link = button("chat-link", title, () => openChat(chat.id));
    link.title = title;
    if (chat.id === state.chatId) link.setAttribute("aria-current", "page");

    const remove = button("chat-delete", undefined, () => {
      if ("confirm" in remove.dataset) return deleteChat(chat.id);
      remove.dataset.confirm = "";
      remove.textContent = "Delete";
    });
    remove.innerHTML = ICONS.close;
    remove.setAttribute("aria-label", `Delete “${title}”`);
    remove.addEventListener("blur", () => {
      delete remove.dataset.confirm;
      remove.innerHTML = ICONS.close;
    });

    item.append(link, remove);
    items.append(item);
  }
}

export async function openChat(id) {
  closeDrawers();
  if (state.busy || id === state.chatId) return;
  try {
    const chat = await getJson(`/api/chats/${id}`);
    showChat(chat.id, chat.title, chat.turns);
  } catch (error) {
    toast(`Couldn't open the chat: ${error.message}`);
  }
}

export function newChat() {
  closeDrawers();
  if (state.busy) return;
  showChat(crypto.randomUUID(), "", []);
  input.focus();
}

export function showChat(id, title, turns) {
  state.chatId = id;
  state.title = title;
  state.turns = turns;
  messagesEl.replaceChildren();
  turns.forEach(renderSavedTurn);
  emptyEl.hidden = turns.length > 0;
  showTitle();
  renderChatList();
  showPanel({ view: "sources" });
  scrollToEnd(true);
}

export async function deleteChat(id) {
  if (state.busy && id === state.chatId) return;
  await api(`/api/chats/${id}`, { method: "DELETE" });
  if (id === state.chatId) showChat(crypto.randomUUID(), "", []);
  await loadChats();
  toast("Chat deleted");
}

export function showTitle() {
  const title = $("chat-title");
  title.textContent = state.title || "New chat";
  title.disabled = !state.turns.length;
  document.title = state.title ? `${state.title} · ${state.appName}` : state.appName;
}

export function startRename() {
  const title = $("chat-title");
  const field = el("input", "title-field");
  field.value = state.title;
  field.maxLength = 80;
  field.setAttribute("aria-label", "Chat name");
  title.hidden = true;
  title.after(field);
  field.focus();
  field.select();

  field.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); field.blur(); }
    if (event.key === "Escape") { event.stopPropagation(); field.dataset.cancel = ""; field.blur(); }
  });
  field.addEventListener("blur", async () => {
    const name = field.value.trim();
    field.remove();
    title.hidden = false;
    if ("cancel" in field.dataset || !name || name === state.title) return;
    try {
      await sendJson(`/api/chats/${state.chatId}`, "PATCH", { title: name });
      state.title = name;
      showTitle();
      loadChats();
    } catch (error) {
      toast(`Couldn't rename: ${error.message}`);
    }
  }, { once: true });
}
