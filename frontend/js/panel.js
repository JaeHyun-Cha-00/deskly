import { getJson, sendJson } from "./api.js";
import { eventTime, longDate, shortDate } from "./dates.js";
import { $, ICONS, WIDE, app, button, el, toast } from "./dom.js";
import { state } from "./state.js";

// steps that opened mail ("read_email" is from chats saved before the thread tools)
export const OPENED = new Set(["get_message", "get_thread", "get_draft", "read_email"]);

export function uniqueMails(steps) {
  const found = new Map();
  for (const step of steps) for (const mail of step.mails) if (!found.has(mail.id)) found.set(mail.id, mail);
  return [...found.values()];
}

// the app a step belongs to; the server names it ("Gmail", "GitHub")
export function stepApp(step) {
  return step.app || "Other";
}

// the apps one answer used, in the order it first used them
export function stepApps(steps) {
  return [...new Set(steps.map(stepApp))];
}

export function chatMails() {
  const steps = state.turns.flatMap((turn) => turn.steps);
  const opened = uniqueMails(steps.filter((s) => OPENED.has(s.tool)));
  const openedIds = new Set(opened.map((m) => m.id));
  const found = uniqueMails(steps.filter((s) => !OPENED.has(s.tool))).filter((m) => !openedIds.has(m.id));
  return { opened, found };
}

export function chatEvents() {
  const found = new Map();
  // chats saved before Calendar have no events on their steps
  for (const step of state.turns.flatMap((turn) => turn.steps)) {
    for (const event of step.events || []) if (!found.has(event.id)) found.set(event.id, event);
  }
  return [...found.values()].sort((a, b) => a.start.localeCompare(b.start));
}

export function chatFiles() {
  const found = new Map();
  for (const step of state.turns.flatMap((turn) => turn.steps)) {
    for (const file of step.files || []) if (!found.has(file.path)) found.set(file.path, file);
  }
  return [...found.values()];
}

export function panelIsOpen() {
  return app.dataset.panel === "open";
}

export function setPanel(open) {
  app.dataset.panel = open ? "open" : "closed";
  $("toggle-panel").setAttribute("aria-expanded", String(open));
  updateScrim();
}

export function showPanel(view, open) {
  state.panel = view;
  renderPanel();
  if (open) setPanel(true);
  if (open && !WIDE.matches) setTimeout(() => $("panel-close").focus(), 50);
}

export function renderPanel() {
  const view = state.panel;
  const body = $("panel-body");
  $("panel-back").hidden = view.view === "sources";

  if (view.view === "sources") {
    $("panel-title").textContent = "Sources";
    const { opened, found } = chatMails();
    const events = chatEvents();
    const files = chatFiles();
    body.replaceChildren();
    if (!opened.length && !found.length && !events.length && !files.length) {
      body.append(el("p", "panel-empty", "Everything I look at in this chat is listed here, so you can check what my answers are based on."));
    }
    if (opened.length) body.append(mailSection("Opened", opened));
    if (found.length) body.append(mailSection("Found in searches", found));
    if (events.length) body.append(eventSection("Events", events));
    if (files.length) body.append(fileSection("Files", files));
  }
  if (view.view === "turn") {
    $("panel-title").textContent = "What I looked at";
    body.replaceChildren(turnSteps(view.turn));
  }
  if (view.view === "files") {
    $("panel-title").textContent = "Files";
    body.replaceChildren(el("p", "panel-note", view.step.label), fileSection(null, view.step.files));
  }
  if (view.view === "events") {
    $("panel-title").textContent = "Calendar";
    body.replaceChildren(el("p", "panel-note", view.step.label), eventSection(null, view.step.events));
  }
  if (view.view === "search") {
    $("panel-title").textContent = OPENED.has(view.step.tool) ? "Conversation" : "Search results";
    body.replaceChildren(el("p", "panel-note", view.step.label), mailSection(null, view.step.mails));
  }
  if (view.view === "mail") renderMail(view.id);
  markOpenMail();
}

// one answer's steps, grouped by app; each finished step can open what it found
function turnSteps(turn) {
  const wrap = el("div", "turn-steps");
  wrap.append(el("p", "panel-note", `For “${turn.user.length > 80 ? `${turn.user.slice(0, 80)}…` : turn.user}”`));
  for (const app of stepApps(turn.steps)) {
    const section = el("section", "panel-section");
    section.append(el("h3", "panel-section-title", app));
    const list = el("ol", "step-list");
    for (const step of turn.steps.filter((s) => stepApp(s) === app)) {
      const item = el("li", "step");
      if (step.done) item.dataset.done = "";
      item.append(el("span", "step-label", step.label));
      if (step.done && step.result) item.append(stepResult(step));
      list.append(item);
    }
    section.append(list);
    wrap.append(section);
  }
  return wrap;
}

function stepResult(step) {
  const back = state.panel;
  if (step.files?.length) return resultButton(step, "Show these files", () => showPanel({ view: "files", step, back }, true));
  if (step.events?.length) return resultButton(step, "Show these events", () => showPanel({ view: "events", step, back }, true));
  if (!step.mails?.length) return el("span", "step-result", step.result);
  // one opened mail opens itself; a conversation or a search shows its list
  const opened = OPENED.has(step.tool) && step.mails.length === 1;
  return resultButton(step, opened ? "Show this mail" : "Show what this search found",
    () => (opened ? openMail(step.mails[0].id) : showPanel({ view: "search", step, back }, true)));
}

function resultButton(step, title, onClick) {
  const result = button("step-result", step.result, onClick);
  result.title = title;
  return result;
}

export function mailSection(title, mails) {
  const section = el("section", "panel-section");
  if (title) section.append(el("h3", "panel-section-title", `${title}, ${mails.length}`));
  const list = el("ul", "mail-list");
  for (const mail of mails) {
    const row = button("mail-row", undefined, () => openMail(mail.id));
    row.dataset.mailId = mail.id;
    if (mail.unread) {
      row.dataset.unread = "";
      row.setAttribute("aria-label", `Unread: ${mail.from}, ${mail.subject}`);
    }
    row.append(
      el("span", "mail-row-from", mail.from),
      el("span", "mail-row-date", shortDate(mail.date)),
      el("span", "mail-row-subject", mail.subject || "(no subject)"),
    );
    if (mail.snippet) row.append(el("span", "mail-row-snippet", mail.snippet));
    const item = el("li");
    item.append(row);
    list.append(item);
  }
  section.append(list);
  return section;
}

export function eventSection(title, events) {
  const section = el("section", "panel-section");
  if (title) section.append(el("h3", "panel-section-title", `${title}, ${events.length}`));
  const list = el("ul", "mail-list");
  for (const event of events) {
    // a row opens the event in Google Calendar when there is a link
    const row = el(event.link ? "a" : "div", "mail-row event-row");
    if (event.link) {
      row.href = event.link;
      row.target = "_blank";
      row.rel = "noopener noreferrer";
      row.title = "Open in Google Calendar";
    }
    row.append(
      el("span", "mail-row-from", event.title || "(no title)"),
      el("span", "mail-row-subject", eventTime(event)),
    );
    if (event.location) row.append(el("span", "mail-row-snippet", event.location));
    const item = el("li");
    item.append(row);
    list.append(item);
  }
  section.append(list);
  return section;
}

function fileSize(size) {
  if (size === null || size === undefined) return "";
  const units = ["B", "KB", "MB", "GB"];
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
  return `${unit ? size.toFixed(1) : size} ${units[unit]}`;
}

export function fileSection(title, files) {
  const section = el("section", "panel-section");
  if (title) section.append(el("h3", "panel-section-title", `${title}, ${files.length}`));
  const list = el("ul", "mail-list");
  for (const file of files) {
    // a row shows the file in Finder; the app checks the path again before opening anything
    const row = button("mail-row file-row", undefined, async () => {
      try {
        await sendJson("/api/files/reveal", "POST", { path: file.path });
      } catch (error) {
        toast(`Couldn't show it: ${error.message}`);
      }
    });
    row.title = "Show in Finder";
    row.append(
      el("span", "mail-row-from", file.name),
      el("span", "mail-row-date", [file.kind, fileSize(file.size)].filter(Boolean).join(" · ")),
      el("span", "mail-row-snippet", file.short),
    );
    const item = el("li");
    item.append(row);
    list.append(item);
  }
  section.append(list);
  return section;
}

export function openMail(id) {
  const back = state.panel.view === "mail" ? state.panel.back : state.panel;
  showPanel({ view: "mail", id, back }, true);
}

export async function renderMail(id) {
  const body = $("panel-body");
  $("panel-title").textContent = "Mail";

  if (!state.mails.has(id)) {
    const skeleton = el("div", "skeleton");
    skeleton.append(el("span"), el("span"), el("span"), el("span"), el("span"));
    body.replaceChildren(skeleton);
    try {
      state.mails.set(id, await getJson(`/api/mail/${encodeURIComponent(id)}`));
    } catch (error) {
      if (state.panel.id === id) body.replaceChildren(el("p", "panel-empty", `Couldn't open this mail: ${error.message}`));
      return;
    }
  }
  // another mail was picked meanwhile
  if (state.panel.view !== "mail" || state.panel.id !== id) return;

  const mail = state.mails.get(id);
  const memo = el("article", "memo");
  memo.append(el("h3", "memo-subject", mail.subject || "(no subject)"));

  const fields = el("dl", "memo-fields");
  for (const [name, value] of [["From", mail.from], ["To", mail.to], ["Date", longDate(mail.date)]]) {
    fields.append(el("dt", null, name), el("dd", null, value || ""));
  }
  memo.append(fields, el("div", "memo-body", mail.body || "(This mail has no text.)"));

  const foot = el("footer", "memo-foot");
  const link = el("a", "quiet-button");
  link.href = `https://mail.google.com/mail/u/0/#all/${encodeURIComponent(mail.id)}`;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.innerHTML = `${ICONS.external}<span>Open in Gmail</span>`;
  foot.append(link);
  memo.append(foot);
  body.replaceChildren(memo);
  body.scrollTop = 0;
}

export function markOpenMail() {
  const openId = state.panel.view === "mail" && panelIsOpen() ? state.panel.id : null;
  document.querySelectorAll("[data-mail-id]").forEach((node) => {
    node.setAttribute("aria-current", String(node.dataset.mailId === openId));
  });
}

export function updateScrim() {
  const railOpen = app.dataset.rail === "open";
  const panelOver = !WIDE.matches && panelIsOpen();
  $("scrim").hidden = !(railOpen || panelOver);
  document.querySelector(".chat").inert = railOpen || panelOver;
  $("rail").inert = panelOver || (window.innerWidth <= 760 && !railOpen);
  $("panel").inert = !panelIsOpen();
  markOpenMail();
}

export function closeDrawers() {
  app.dataset.rail = "closed";
  if (!WIDE.matches) app.dataset.panel = "closed";
  $("toggle-panel").setAttribute("aria-expanded", String(panelIsOpen()));
  updateScrim();
}
