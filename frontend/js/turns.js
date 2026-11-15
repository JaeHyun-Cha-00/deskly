import { send } from "./ask.js";
import { longDate, shortDate } from "./dates.js";
import { $, ICONS, button, copyText, el, input, messagesEl, thread, toast } from "./dom.js";
import { renderMarkdown } from "./markdown.js";
import { markOpenMail, openMail, showPanel, uniqueMails } from "./panel.js";

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
  return { turn, article, slip, letter, cards, actions, steps: new Map(), draft: "", frame: 0 };
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

  if (!step.mails.length) {
    item.append(el("span", "step-result", step.result));
    return;
  }
  const opened = step.tool === "read_email";
  const result = button("step-result", step.result, () => opened ? openMail(step.mails[0].id) : showPanel({ view: "search", step }, true));
  result.title = opened ? "Show this mail" : "Show what this search found";
  item.append(result);
}

export function setWaiting(view, text) {
  view.letter.className = "letter waiting";
  view.letter.textContent = text;
}

export function streamToken(view, text) {
  view.draft += text;
  if (view.frame) return;
  view.frame = requestAnimationFrame(() => {
    view.frame = 0;
    view.letter.className = "letter streaming";
    view.letter.innerHTML = renderMarkdown(view.draft);
    scrollToEnd();
  });
}

export function renderAnswer(view, text) {
  cancelAnimationFrame(view.frame);
  view.frame = 0;
  view.draft = "";
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
  if (text) renderAnswer(view, text);
  else setWaiting(view, "");
  view.letter.classList.add("stopped");
  view.letter.after(el("p", "stopped-note", "Stopped"));
}

export function renderError(view, message, retryText) {
  view.letter.className = "letter error";
  view.letter.replaceChildren(el("p", null, message));
  if (retryText) view.letter.append(button("quiet-button", "Try again", () => send(retryText)));
}

export function renderCards(view) {
  const opened = uniqueMails(view.turn.steps.filter((s) => s.tool === "read_email"));
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
  if (turn.stopped) showStopped(view, turn.answer);
  else if (turn.answer) renderAnswer(view, turn.answer);
  else renderError(view, turn.error || "No reply came back.", null);
  renderCards(view);
}
