import json

from config import SETTINGS_FILE

CHOICES = {
    "theme": ["system", "light", "dark"],
    "length": ["short", "detailed"],
}

DEFAULTS = {"theme": "system", "length": "short"}

def load():
    saved = json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
    return DEFAULTS | {key: value for key, value in saved.items() if value in CHOICES.get(key, [])}

def update(changes):
    settings = load()
    for key, value in changes.items():
        if value not in CHOICES.get(key, []):
            raise ValueError(f"{key} can't be {value!r}")
        settings[key] = value
    SETTINGS_FILE.write_text(json.dumps(settings, indent=1))
    return settings
