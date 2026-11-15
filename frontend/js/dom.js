export const $ = (id) => document.getElementById(id);

export const app = $("app");
export const thread = $("thread");
export const messagesEl = $("messages");
export const emptyEl = $("empty");
export const form = $("composer");
export const input = $("input");
export const sendButton = $("send");
export const palette = $("palette");
export const paletteInput = $("palette-input");
export const paletteList = $("palette-list");
export const settingsDialog = $("settings");

export const IS_MAC = /Mac|iPhone|iPad/.test(navigator.platform);
export const MOD = IS_MAC ? "⌘" : "Ctrl";
export const WIDE = window.matchMedia("(min-width: 1180px)");

export const ICONS = {
  close: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/></svg>',
  external: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
};

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function button(className, text, onClick) {
  const node = el("button", className, text);
  node.type = "button";
  node.addEventListener("click", onClick);
  return node;
}

export function store(key, value) {
  try { localStorage.setItem(key, value); } catch {}
}

export function toast(text) {
  const node = el("div", "toast", text);
  $("toasts").append(node);
  setTimeout(() => {
    node.dataset.leaving = "";
    setTimeout(() => node.remove(), 260);
  }, 2400);
}

export function isTyping(target) {
  return target.matches("input, textarea, select") || target.isContentEditable;
}

export async function copyText(text) {
  // the clipboard API isn't always allowed inside the desktop window
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const box = el("textarea");
    box.value = text;
    box.style.position = "fixed";
    box.style.opacity = "0";
    document.body.append(box);
    box.select();
    document.execCommand("copy");
    box.remove();
  }
}
