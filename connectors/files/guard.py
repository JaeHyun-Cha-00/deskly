import re
from pathlib import Path

HOME = Path.home()

# file names that look like keys, tokens or secrets (checked for files only, so a Keynote
# ".key" document, which is a folder, still opens)
SECRET = re.compile(
    r"^id_[a-z0-9]+(\.pub)?$|\.(pem|key|p12|pfx|keychain|keychain-db|kdbx)$|credentials.*\.json$|token.*\.json$",
    re.IGNORECASE,
)

def blocked_reason(real):
    # why a resolved path is off-limits, or "" if it's fine
    if real != HOME and HOME not in real.parents:
        return "it is outside your home folder"
    parts = real.relative_to(HOME).parts
    if any(part.startswith(".") for part in parts):
        return "hidden files and folders are off-limits"
    if parts and parts[0] == "Library":
        return "the Library folder holds app data and passwords"
    if real.is_file() and SECRET.search(real.name):
        return "it looks like a key or a password file"
    return ""

def safe_path(raw):
    # turns what the model asked for into a real path, or refuses.
    # resolve() follows "../" and symlinks first, so neither can sneak past the checks.
    path = Path(str(raw).strip()).expanduser()
    if not path.is_absolute():
        path = HOME / path
    real = path.resolve()
    reason = blocked_reason(real)
    if reason:
        raise PermissionError(f"I can't open {raw}: {reason}.")
    if not real.exists():
        raise FileNotFoundError(f"There is nothing at {raw}.")
    return real

def allowed(path):
    try:
        return not blocked_reason(Path(path).resolve())
    except (OSError, ValueError):
        return False

def short(path):
    # "/Users/me/Documents/a.pdf" becomes "~/Documents/a.pdf"
    path = Path(path)
    return "~" if path == HOME else f"~/{path.relative_to(HOME)}" if HOME in path.parents else str(path)
