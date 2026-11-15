import { getJson } from "./api.js";
import { longDate, shortDate } from "./dates.js";
import { $, ICONS, WIDE, app, button, el } from "./dom.js";
import { state } from "./state.js";

export function uniqueMails(steps) {
  const found = new Map();
  for (const step of steps) for (const mail of step.mails) if (!found.has(mail.id)) found.set(mail.id, mail);
  return [...found.values()];
}

export function chatMails() {
  const steps = state.turns.flatMap((turn) => turn.steps);
  const opened = uniqueMails(steps.filter((s) => s.tool === "read_email"));
  const openedIds = new Set(opened.map((m) => m.id));
  const found = uniqueMails(steps.filter((s) => s.tool !== "read_email")).filter((m) => !openedIds.has(m.id));
  return { opened, found };
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
    body.replaceChildren();
    if (!opened.length && !found.length) {
      body.append(el("p", "panel-empty", "Everything I look at in this chat is listed here, so you can check what my answers are based on."));
    }
    if (opened.length) body.append(mailSection("Opened", opened));
    if (found.length) body.append(mailSection("Found in searches", found));
  }
  if (view.view === "search") {
    $("panel-title").textContent = "Search results";
    body.replaceChildren(el("p", "panel-note", view.step.label), mailSection(null, view.step.mails));
  }
  if (view.view === "mail") renderMail(view.id);
  markOpenMail();
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
  if (mail.demo) {
    foot.append(el("p", "panel-note", "A made-up mail for demo mode."));
  } else {
    const link = el("a", "quiet-button");
    link.href = `https://mail.google.com/mail/u/0/#all/${encodeURIComponent(mail.id)}`;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.innerHTML = `${ICONS.external}<span>Open in Gmail</span>`;
    foot.append(link);
  }
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
