from config import APP_DIR

# laptop files need no sign-in; connecting only turns them on
ON_FILE = APP_DIR / "files_on"

def connect():
    ON_FILE.touch()

def is_connected():
    return ON_FILE.exists()

def sign_out():
    ON_FILE.unlink(missing_ok=True)
