# Deskly

A personal AI agent for the laptop. It starts with Gmail (read only) and will grow one area at a time.

## Setup

1. `uv sync`
2. Put your OpenRouter key in `.env`:
   ```
   OPENROUTER_API_KEY=your_key
   ```
3. Google: create a Google Cloud project, enable the Gmail API, add yourself as a test user, and create an OAuth client of type **Desktop app**. Save its JSON as `credentials.json` in `~/Library/Application Support/Deskly/`.

## Run

```
uv run python -m desktop                     # the app in its own window (the server runs inside it)
ASSISTANT_DEMO=1 uv run python -m desktop    # the same with made-up mail (no Gmail sign-in)
uv run python -m backend                     # the browser version: opens http://127.0.0.1:8765
ASSISTANT_PORT=8766 uv run python -m backend # another port, if 8765 is taken
uv run python -m agent                       # chat with the agent in the terminal
uv run python -m connectors.gmail.read       # sign in, then print your 5 newest subjects
```

The first Gmail use opens the browser for the Google sign-in (or Connectors, then Connect, in the chat screen) and saves the sign-in as `token.json` in the same folder. The server only listens on 127.0.0.1 and refuses requests from other websites. Saved chats and settings also go in `~/Library/Application Support/Deskly/` (on this laptop only; only you can open the folder). `.env` stays in the project folder for now and is git-ignored.

## Structure

Each part has its own folder, and a part only uses the parts below it:

```
desktop/      the app window (pywebview): starts the backend and shows the frontend in it
frontend/     the screen (HTML, CSS, JS); talks to the backend over HTTP only
backend/      the local web server: API routes, security, saved chats, settings
agent/        the agent: model, prompt, tools, demo mail; knows nothing about the web
connectors/   outside services: Google sign-in, Gmail API; knows nothing about the agent
config.py     reads .env and config.yaml, shared by all
```
