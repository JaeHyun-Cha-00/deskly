import { HEADERS, api } from "./api.js";
import { loadChats, showTitle } from "./chats.js";
import { emptyEl, form, input, sendButton, toast } from "./dom.js";
import { loadMemory } from "./memory.js";
import { renderPanel } from "./panel.js";
import { state } from "./state.js";
import { loadStatus, showNotice } from "./status.js";
import { addUserMessage, createTurnView, finishStep, renderAnswer, renderApproval, renderCards, renderError, renderStep, scrollToEnd, setWaiting, showContext, showStopped, startTimer, stopTimer, streamToken } from "./turns.js";

async function stopAnswer() {
  const controller = state.controller;
  sendButton.disabled = true;
  await api(`/api/chats/${state.chatId}/stop`, { method: "POST" }).catch(() => {});
  controller.abort();
  setTimeout(() => loadChats().catch(() => {}), 1500);
}

function setBusy(busy) {
  state.busy = busy;
  sendButton.textContent = busy ? "Stop" : "Send";
  sendButton.classList.toggle("stop", busy);
  sendButton.disabled = false;
}

async function readEvents(response, onEvent) {
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

function handleEvent(view, event) {
  const turn = view.turn;
  // picking up a paused answer sends the paused step again
  if (event.type === "step" && turn.steps.some((s) => s.id === event.id)) return;
  if (event.type === "step") {
    const step = { id: event.id, label: event.label, done: false, tool: event.tool || "", app: event.app || "", result: "", mails: [], events: [], files: [] };
    turn.steps.push(step);
    renderStep(view, step);
    // text before a step was the agent thinking aloud
    view.draft = "";
    setWaiting(view, "Looking things up");
  }
  if (event.type === "step_done") {
    const step = turn.steps.find((s) => s.id === event.id);
    if (step) {
      Object.assign(step, { done: true, tool: event.tool, app: event.app || step.app, result: event.result, mails: event.mails, events: event.events || [], files: event.files || [] });
      finishStep(view, step);
      renderCards(view);
      if (state.panel.view === "sources") renderPanel();
    }
  }
  if (event.type === "token") streamToken(view, event.text);
  if (event.type === "notice") {
    // an app couldn't be used for this answer; the Connectors light may have changed too
    toast(event.message);
    loadStatus();
  }
  if (event.type === "usage") {
    turn.context = { tokens: event.tokens, limit: event.limit };
    showContext(view);
  }
  if (event.type === "answer") {
    turn.answer = event.text;
    renderAnswer(view, event.text);
  }
  if (event.type === "approval") {
    turn.approval = { requests: event.requests, state: "waiting" };
    renderApproval(view, turn.approval);
    setWaiting(view, "Waiting for your OK");
  }
  if (event.type === "decided" || event.type === "expired") {
    turn.approval = { ...turn.approval, state: event.type === "expired" ? "expired" : event.state };
    renderApproval(view, turn.approval);
    setWaiting(view, event.type === "expired" ? "" : "Working on it");
    if (event.type === "decided") startTimer(view);
  }
  if (event.type === "error") {
    turn.error = event.message;
    renderError(view, event.message, turn.user);
    loadStatus();
  }
  if (event.type === "done") {
    turn.seconds = event.seconds;
    stopTimer(view);
    if (event.stopped) {
      turn.stopped = true;
      turn.answer = turn.answer || view.draft.trim();
      showStopped(view, turn.answer);
    }
    state.title = state.title || event.chat.title;
    showTitle();
    loadChats();
    // the agent may have saved or forgotten something
    loadMemory();
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
  await follow(view, "/api/chat", { chat_id: state.chatId, text }, text);
}

// the user's answer on an approval card: the paused answer picks up from there
export async function decide(view, decisions) {
  if (state.busy || state.offline) return;
  setBusy(true);
  view.approval?.querySelectorAll("button, input, textarea").forEach((node) => { node.disabled = true; });
  setWaiting(view, "Working on it");
  await follow(view, `/api/chats/${state.chatId}/decide`, { decisions }, null);
}

// sends one request and shows the answer's events in `view` as they arrive
async function follow(view, url, body, retryText) {
  const turn = view.turn;
  state.controller = new AbortController();
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify(body),
      signal: state.controller.signal,
    });
    if (!response.ok) {
      const answer = await response.json().catch(() => ({}));
      throw new Error(answer.detail || `the app answered ${response.status}`);
    }
    await readEvents(response, (event) => handleEvent(view, event));
    const asking = ["waiting", "expired"].includes(turn.approval?.state);
    if (!turn.answer && !turn.error && !turn.stopped && !asking) renderError(view, "No reply came back.", retryText);
  } catch (error) {
    if (error.name === "AbortError") {
      turn.stopped = true;
      showStopped(view, view.draft.trim());
    } else if (error instanceof TypeError) {
      turn.error = "Can't reach the app.";
      renderError(view, turn.error, retryText);
      loadStatus();
    } else {
      turn.error = error.message;
      renderError(view, error.message, retryText);
    }
  } finally {
    // however it ended (done, error, stop), the clock stops
    if (view.timer) stopTimer(view);
    view.article.classList.add("settled");
    setBusy(false);
    showNotice();
    input.focus();
  }
}

function resizeInput() {
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

