import { HEADERS, api } from "./api.js";
import { loadChats, showTitle } from "./chats.js";
import { emptyEl, form, input, sendButton } from "./dom.js";
import { renderPanel } from "./panel.js";
import { state } from "./state.js";
import { loadStatus, showNotice } from "./status.js";
import { addUserMessage, createTurnView, finishStep, renderAnswer, renderCards, renderError, renderStep, scrollToEnd, setWaiting, showStopped, streamToken } from "./turns.js";

export async function stopAnswer() {
  const controller = state.controller;
  sendButton.disabled = true;
  await api(`/api/chats/${state.chatId}/stop`, { method: "POST" }).catch(() => {});
  controller.abort();
  setTimeout(() => loadChats().catch(() => {}), 1500);
}

export function setBusy(busy) {
  state.busy = busy;
  sendButton.textContent = busy ? "Stop" : "Send";
  sendButton.classList.toggle("stop", busy);
  sendButton.disabled = false;
}

export async function readEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop();
    for (const chunk of chunks) {
      if (chunk.startsWith("data: ")) onEvent(JSON.parse(chunk.slice(6)));
    }
  }
}

export function handleEvent(view, event) {
  const turn = view.turn;
  if (event.type === "step") {
    const step = { id: event.id, label: event.label, done: false, tool: "", result: "", mails: [] };
    turn.steps.push(step);
    renderStep(view, step);
    // text before a step was the agent thinking aloud
    view.draft = "";
    setWaiting(view, "Looking things up");
  }
  if (event.type === "step_done") {
    const step = turn.steps.find((s) => s.id === event.id);
    if (step) {
      Object.assign(step, { done: true, tool: event.tool, result: event.result, mails: event.mails });
      finishStep(view, step);
      renderCards(view);
      if (state.panel.view === "sources") renderPanel();
    }
  }
  if (event.type === "token") streamToken(view, event.text);
  if (event.type === "answer") {
    turn.answer = event.text;
    renderAnswer(view, event.text);
  }
  if (event.type === "error") {
    turn.error = event.message;
    renderError(view, event.message, turn.user);
    loadStatus();
  }
  if (event.type === "done") {
    if (event.stopped) {
      turn.stopped = true;
      turn.answer = turn.answer || view.draft.trim();
      showStopped(view, turn.answer);
    }
    state.title = state.title || event.chat.title;
    showTitle();
    loadChats();
  }
  scrollToEnd();
}

export async function send(text) {
  text = text.trim();
  if (state.busy || !text || state.offline || !state.modelKey) return;
  setBusy(true);
  emptyEl.hidden = true;

  const turn = { user: text, at: new Date().toISOString(), steps: [], answer: "", error: "" };
  state.turns.push(turn);
  state.title = state.title || text.slice(0, 60);
  showTitle();
  addUserMessage(text, turn.at, true);
  const view = createTurnView(turn, true);
  scrollToEnd(true);
  state.controller = new AbortController();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({ chat_id: state.chatId, text }),
      signal: state.controller.signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `the app answered ${response.status}`);
    }
    await readEvents(response, (event) => handleEvent(view, event));
    if (!turn.answer && !turn.error && !turn.stopped) renderError(view, "No reply came back.", text);
  } catch (error) {
    if (error.name === "AbortError") {
      turn.stopped = true;
      showStopped(view, view.draft.trim());
    } else if (error instanceof TypeError) {
      turn.error = "Can't reach the app.";
      renderError(view, turn.error, text);
      loadStatus();
    } else {
      turn.error = error.message;
      renderError(view, error.message, text);
    }
  } finally {
    view.article.classList.add("settled");
    setBusy(false);
    showNotice();
    input.focus();
  }
}

export function resizeInput() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

input.addEventListener("input", resizeInput);

input.addEventListener("keydown", (event) => {
  // isComposing: Enter that finishes an IME word must not send
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (state.busy) stopAnswer();
  if (state.busy) return;
  const text = input.value;
  input.value = "";
  resizeInput();
  send(text);
});

