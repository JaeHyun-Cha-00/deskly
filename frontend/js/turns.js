import { decide, send } from "./ask.js";
import { longDate, shortDate } from "./dates.js";
import { $, ICONS, button, copyText, el, input, messagesEl, thread, toast } from "./dom.js";
import { renderMarkdown } from "./markdown.js";
import { OPENED, markOpenMail, openMail, showPanel, uniqueMails } from "./panel.js";

export function nearBottom() {
  return thread.scrollHeight - thread.scrollTop - thread.clientHeight < 160;
}

export function scrollToEnd(force) {
  if (force || nearBottom()) thread.scrollTop = thread.scrollHeight;
  $("jump-latest").hidden = nearBottom();
}

thread.addEventListener("scroll", () => { $("jump-latest").hidden = nearBottom(); }, { passive: true });
$("jump-latest").addEventListener("click", () => {
  thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
  input.focus();
});

export function addUserMessage(text, at, live) {
  const wrap = el("div", `msg msg-user${live ? " arriving" : ""}`);
  const bubble = el("p", null, text);
  if (at) bubble.title = longDate(at);
  wrap.append(bubble);
  messagesEl.append(wrap);
}

export function createTurnView(turn, live) {
  const article = el("article", `msg msg-assistant no-steps${live ? " arriving" : ""}`);
  const slip = el("ol", "slip");
  slip.setAttribute("aria-label", "What I looked at");
  slip.append(el("li", "slip-title", "What I looked at"));

  const body = el("div", "turn-body");
  const letter = el("div", "letter waiting", "Thinking");
  const cards = el("div", "mail-cards");
  const actions = el("div", "letter-actions");
  cards.hidden = true;
  actions.hidden = true;

  body.append(letter, cards, actions);
  article.append(slip, body);
  messagesEl.append(article);
  return { turn, article, slip, letter, cards, actions, steps: new Map(), draft: "", shown: 0, frame: 0 };
}

export function renderStep(view, step) {
  view.article.classList.remove("no-steps");
  const item = el("li", "step");
  item.append(el("span", "step-label", step.label));
  view.slip.append(item);
  view.steps.set(step.id, item);
  if (step.done) finishStep(view, step);
}

export function finishStep(view, step) {
  const item = view.steps.get(step.id);
  if (!item) return;
  item.dataset.done = "";
  if (!step.result) return;

  if (step.files?.length) {
    const result = button("step-result", step.result, () => showPanel({ view: "files", step }, true));
    result.title = "Show these files";
    item.append(result);
    return;
  }
  if (step.events?.length) {
    const result = button("step-result", step.result, () => showPanel({ view: "events", step }, true));
    result.title = "Show these events";
    item.append(result);
    return;
  }
  if (!step.mails.length) {
    item.append(el("span", "step-result", step.result));
    return;
  }
  // one opened mail opens itself; a conversation or a search shows its list
  const opened = OPENED.has(step.tool) && step.mails.length === 1;
  const result = button("step-result", step.result, () => opened ? openMail(step.mails[0].id) : showPanel({ view: "search", step }, true));
  result.title = opened ? "Show this mail" : "Show what this search found";
  item.append(result);
}

export function setWaiting(view, text) {
  cancelAnimationFrame(view.frame);
  view.frame = 0;
  view.shown = 0;
  view.letter.className = "letter waiting";
  view.letter.textContent = text;
}

// text arrives from the network in uneven bursts; show it at a steady pace
export function streamToken(view, text) {
  view.draft += text;
  if (!view.frame) view.frame = requestAnimationFrame(() => reveal(view));
}

function reveal(view) {
  // a bigger backlog is shown faster, so the text never falls far behind
  const backlog = view.draft.length - view.shown;
  view.shown += Math.max(1, Math.ceil(backlog / 12));
  view.letter.className = "letter streaming";
  view.letter.innerHTML = renderMarkdown(view.draft.slice(0, view.shown));
  scrollToEnd();

  if (view.shown < view.draft.length) {
    view.frame = requestAnimationFrame(() => reveal(view));
  } else {
    view.frame = 0;
    if (view.final !== undefined) renderAnswer(view, view.final);
  }
}

export function renderAnswer(view, text, now) {
  // let the streamed text finish appearing before the final answer replaces it
  if (view.frame && !now) {
    view.final = text;
    return;
  }
  cancelAnimationFrame(view.frame);
  view.frame = 0;
  view.draft = "";
  view.shown = 0;
  view.final = undefined;
  view.letter.className = "letter";
  view.letter.innerHTML = renderMarkdown(text);

  const copy = button("quiet-button", undefined, async () => {
    await copyText(text);
    toast("Copied");
  });
  copy.innerHTML = `${ICONS.copy}<span>Copy</span>`;
  view.actions.replaceChildren(copy);
  view.actions.hidden = false;
}

export function showStopped(view, text) {
  if (text) renderAnswer(view, text, true);
  else setWaiting(view, "");
  view.letter.classList.add("stopped");
  view.letter.after(el("p", "stopped-note", "Stopped"));
}

const DECIDED = {
  approved: "Approved",
  edited: "Approved with your changes",
  rejected: "Rejected",
  expired: "Expired. Ask again and I'll prepare it again.",
};

// the fields an edit can change, for tools that may leave some out
const FIELDS = { create_event: ["title", "start", "end", "location", "description"] };

const fieldName = (key) => key.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());

function details(args) {
  const list = el("dl", "approval-fields");
  for (const [key, value] of Object.entries(args)) {
    if (value === "" || (key === "calendar_id" && value === "primary")) continue;
    list.append(el("dt", null, fieldName(key)), el("dd", null, String(value)));
  }
  return list;
}

export function renderApproval(view, approval) {
  view.approval?.remove();
  const card = el("section", "approval");
  card.dataset.state = approval.state;
  card.setAttribute("aria-label", "Needs your OK");
  card.append(el("p", "approval-title", approval.state === "waiting" ? "Needs your OK" : "Your decision"));
  for (const request of approval.requests) {
    card.append(el("p", "approval-text", request.description), details(request.args));
  }

  const actions = el("div", "approval-actions");
  if (approval.state === "waiting") {
    const all = (decision) => approval.requests.map(() => decision);
    actions.append(button("primary-button", "Approve", () => decide(view, all({ type: "approve" }))));
    if (approval.requests.length === 1) actions.append(button("plain-button", "Edit", () => startEdit(view, card, approval.requests[0])));
    actions.append(button("plain-button reject", "Reject", () => startReject(view, card, approval.requests)));
  } else {
    actions.append(el("p", "approval-state", DECIDED[approval.state] || approval.state));
  }
  card.append(actions);
  view.letter.before(card);
  view.approval = card;
  scrollToEnd();
}

function startEdit(view, card, request) {
  const form = el("form", "approval-edit");
  const keys = [...new Set([...(FIELDS[request.name] || []), ...Object.keys(request.args)])];
  for (const key of keys) {
    const value = request.args[key] ?? "";
    const label = el("label", null, fieldName(key));
    const field = el(key === "description" ? "textarea" : "input");
    field.name = key;
    field.value = String(value);
    if (typeof value === "number") field.type = "number";
    label.append(field);
    form.append(label);
  }
  const actions = el("div", "approval-actions");
  const save = el("button", "primary-button", "Approve with changes");
  save.type = "submit";
  actions.append(save, button("plain-button", "Cancel", () => renderApproval(view, view.turn.approval)));
  form.append(actions);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const args = {};
    for (const key of keys) {
      const raw = form.elements[key].value;
      // keep what the agent sent for fields left empty that it never had
      if (raw === "" && !(key in request.args)) continue;
      args[key] = typeof request.args[key] === "number" ? Number(raw) : raw;
    }
    decide(view, [{ type: "edit", edited_action: { name: request.name, args } }]);
  });
  card.querySelectorAll(".approval-fields, .approval-actions").forEach((node) => node.remove());
  card.append(form);
  form.elements[keys[0]]?.focus();
}

function startReject(view, card, requests) {
  const form = el("form", "approval-reject");
  const label = el("label", null, "Why not? (optional, it helps me try again)");
  const reason = el("input");
  reason.name = "reason";
  label.append(reason);
  const actions = el("div", "approval-actions");
  const confirm = el("button", "primary-button reject", "Reject");
  confirm.type = "submit";
  actions.append(confirm, button("plain-button", "Cancel", () => renderApproval(view, view.turn.approval)));
  form.append(label, actions);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = reason.value.trim();
    decide(view, requests.map(() => (message ? { type: "reject", message } : { type: "reject" })));
  });
  card.querySelector(".approval-actions").replaceWith(form);
  reason.focus();
}

export function renderError(view, message, retryText) {
  cancelAnimationFrame(view.frame);
  view.frame = 0;
  view.letter.className = "letter error";
  view.letter.replaceChildren(el("p", null, message));
  if (retryText) view.letter.append(button("quiet-button", "Try again", () => send(retryText)));
}

export function renderCards(view) {
  const opened = uniqueMails(view.turn.steps.filter((s) => OPENED.has(s.tool)));
  view.cards.replaceChildren(...opened.map(mailCard));
  view.cards.hidden = !opened.length;
  markOpenMail();
}

export function mailCard(mail) {
  const card = button("mail-card", undefined, () => openMail(mail.id));
  card.dataset.mailId = mail.id;
  card.append(
    el("span", "mail-card-from", mail.from),
    el("span", "mail-card-date", shortDate(mail.date)),
    el("span", "mail-card-subject", mail.subject || "(no subject)"),
  );
  return card;
}

export function renderSavedTurn(turn) {
  addUserMessage(turn.user, turn.at);
  const view = createTurnView(turn);
  view.article.classList.add("settled");
  turn.steps.forEach((step) => renderStep(view, step));
  if (turn.approval) renderApproval(view, turn.approval);
  if (turn.stopped) showStopped(view, turn.answer);
  else if (turn.answer) renderAnswer(view, turn.answer);
  else if (turn.approval?.state === "waiting") setWaiting(view, "Waiting for your OK");
  else if (turn.approval?.state === "expired") setWaiting(view, "");
  else renderError(view, turn.error || "No reply came back.", null);
  renderCards(view);
}
