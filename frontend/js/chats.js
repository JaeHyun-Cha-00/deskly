import { api, getJson, sendJson } from "./api.js";
import { chatGroup } from "./dates.js";
import { $, ICONS, button, el, emptyEl, input, messagesEl, toast } from "./dom.js";
import { closeDrawers, showPanel } from "./panel.js";
import { state } from "./state.js";
import { renderSavedTurn, scrollToEnd } from "./turns.js";

// chats deleted a moment ago, still undoable: id -> the timer that deletes them for good
const DELETING = new Map();
const UNDO_SECONDS = 5;

export async function loadChats() {
  state.chats = (await getJson("/api/chats")).filter((chat) => !DELETING.has(chat.id));
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

    const remove = button("chat-delete", undefined, () => deleteChat(chat.id));
    remove.innerHTML = ICONS.trash;
    remove.title = "Delete";
    remove.setAttribute("aria-label", `Delete “${title}”`);

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

// One click deletes: the chat disappears at once, and Undo in the message brings it back.
// It is deleted for good only after a few seconds (closing the app before then keeps it).
export function deleteChat(id) {
  if (state.busy && id === state.chatId) return;
  const wasOpen = id === state.chatId;
  DELETING.set(id, setTimeout(async () => {
    DELETING.delete(id);
    await api(`/api/chats/${id}`, { method: "DELETE" }).catch(() => toast("Couldn't delete the chat"));
  }, UNDO_SECONDS * 1000));
  state.chats = state.chats.filter((chat) => chat.id !== id);
  if (wasOpen) showChat(crypto.randomUUID(), "", []);
  else renderChatList();
  toast("Chat deleted", {
    label: "Undo",
    onClick: async () => {
      clearTimeout(DELETING.get(id));
      DELETING.delete(id);
      await loadChats();
      if (wasOpen && !state.busy) openChat(id);
    },
  });
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
