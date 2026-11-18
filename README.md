# Deskly

A personal AI agent that lives on your laptop. You ask in plain words; it reads your mail, calendar, files and apps to answer, and asks you before it changes anything.

- **Connectors:** Gmail, Google Calendar and files on this laptop are built in. GitHub and Slack connect through their official MCP servers.
- **Memory:** it remembers short facts about you across chats. You can see, edit and delete every one in the Memory window.
- **Stays on the laptop:** chats, memory and sign-ins are saved only in `~/Library/Application Support/Deskly`. The model runs through OpenRouter, only on providers that don't store or train on the data.

macOS only for now...

## Setup

You need [OpenRouter](https://openrouter.ai) API key.

1. Install the packages:
   ```
   uv sync
   ```
2. Put your OpenRouter key in `.env` in the project folder:
   ```
   OPENROUTER_API_KEY=your_key
   ```
3. Start the app. Without any connector it works as a general assistant.

### Gmail and Google Calendar

1. In the [Google Cloud console](https://console.cloud.google.com), create a project and enable the **Gmail API** and the **Google Calendar API**.
2. Under OAuth consent screen, add yourself as a **test user**.
3. Create an OAuth client of type **Desktop app**, download its JSON, and save it as `~/Library/Application Support/Deskly/credentials.json`.
4. In Deskly, open **Connectors**, then **Add a connector**, and connect Gmail and Calendar one at a time. Each asks only for its own permission.

While the Google app is in Testing mode, Google ends the sign-in every 7 days; connect again when it asks.

### GitHub and Slack (MCP)

These servers don't let apps register themselves, so you register Deskly once and save its ID:

- **GitHub:** Settings, Developer settings, OAuth Apps, New OAuth App. Use the callback URL `http://127.0.0.1:33418/callback`, then generate a client secret.
- **Slack:** at [api.slack.com/apps](https://api.slack.com/apps), create an app in your own workspace with the redirect URL `http://localhost:33418/callback`, PKCE turned on, and the user scopes listed in `connectors/mcp/servers.py`. With PKCE on there is no secret.

Then save the ID (and secret, if any) in your own terminal. Nothing goes into git or the chat:

```
uv run python -m connectors.mcp.save_client github
uv run python -m connectors.mcp.save_client slack
```

Finally connect it from **Connectors**; the browser opens the app's sign-in page.

## Run

```
uv run python -m desktop                      # the app in its own window
uv run python -m backend                      # the browser version at http://127.0.0.1:8765
uv run python -m agent                        # chat in the terminal (write tools are skipped)
```

The model and a few limits are in `config.yaml`.

## Where things are saved

Everything stays in `~/Library/Application Support/Deskly/`, which only your user can open:

| File | What |
|---|---|
| `credentials.json` | the Google app's ID (you add it) |
| `gmail_token.json`, `calendar_token.json` | each Google app's sign-in |
| `mcp/` | GitHub and Slack app IDs and sign-ins |
| `chats/` | saved chats |
| `memory.json` | what the agent remembers about you |
| `settings.json` | theme, answer length, window see-through |

## Safety

- The server listens on 127.0.0.1 only and refuses requests that don't come from its own page.
- Text from mail, events, files and apps is treated as data, never as instructions (against prompt injection), and can't be saved to memory.
- Files: hidden files, `~/Library` and anything that looks like a key or password file are never read.
- Every write tool waits for your approval. Pending approvals are kept in memory only, so they expire when the app closes.
- Only each company's official MCP server is used.

## Structure

Each part has its own folder, and a part only uses the parts below it:

```
desktop/      the app window (pywebview); starts the server inside it
frontend/     the screen (HTML, CSS, JS, no build step); talks to the server over HTTP only
backend/      the local server: routes, security, saved chats, settings, running an answer
agent/        the agent: model, prompt, memory, and one tools module per app
connectors/   outside services: Google, laptop files, MCP servers; knows nothing about the agent
config.py     reads .env and config.yaml, shared by all
```

**Adding an app** touches two places: its connector in `connectors/APP/` (the API calls, plus the name and description for its Connectors row) and one module in `agent/tools/APP.py` with its tools, prompt and how its steps look. An MCP server is one entry in `connectors/mcp/servers.py`.
