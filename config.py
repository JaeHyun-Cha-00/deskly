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

def write_private(path, text):
    # Saves a file so that a crash mid-write can never leave it half written: the text goes
    # to a temporary file first, which then replaces the old one in one step. Only this user
    # can read it (chats, memory and sign-ins are private).
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)

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
