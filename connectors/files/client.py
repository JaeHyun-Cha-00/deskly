from config import APP_DIR

# how it shows in Connectors
NAME = "Files"
ABOUT = "Find and read files in your home folder. Hidden files, Library and keys stay private."
GROUP = "On this laptop"

# laptop files need no sign-in; connecting only turns them on
ON_FILE = APP_DIR / "files_on"

def connect():
    ON_FILE.touch()

def is_connected():
    return ON_FILE.exists()

def sign_out():
    ON_FILE.unlink(missing_ok=True)
