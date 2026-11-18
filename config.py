import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).parent

APP_DIR = Path.home() / "Library" / "Application Support" / "Deskly"
APP_DIR.mkdir(parents=True, exist_ok=True)
APP_DIR.chmod(0o700)

CHATS_DIR = APP_DIR / "chats"
SETTINGS_FILE = APP_DIR / "settings.json"
MEMORY_FILE = APP_DIR / "memory.json"
CREDENTIALS_FILE = APP_DIR / "credentials.json"

# each app (gmail, calendar) keeps its own Google sign-in
def token_file(app):
    return APP_DIR / f"{app}_token.json"

load_dotenv(ROOT / ".env")

with open(ROOT / "config.yaml") as f:
    config = yaml.safe_load(f)

# only this laptop, never other computers on the network
HOST = "127.0.0.1"
PORT = int(os.getenv("ASSISTANT_PORT", "8765"))
ADDRESS = f"{HOST}:{PORT}"
