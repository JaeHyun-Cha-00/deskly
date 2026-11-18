export const state = {
  chatId: crypto.randomUUID(),
  title: "",
  turns: [],
  chats: [],
  settings: {},
  // app id -> "checking", "connected", "not_connected" or "connecting"; filled from the server
  apps: {},
  appName: "Deskly",
  modelKey: true,
  desktop: false,
  offline: false,
  busy: false,
  controller: null,
  panel: { view: "sources" },
  mails: new Map(),
};
