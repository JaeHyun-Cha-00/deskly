import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

# the port must be set before config.py is read
os.environ.setdefault("ASSISTANT_PORT", str(free_port()))
# tells the page it runs in the desktop app, so it can offer window settings
os.environ["ASSISTANT_DESKTOP"] = "1"

from backend.server import app  # noqa: E402
from config import HOST, PORT, config  # noqa: E402

ICON = Path(__file__).parent / "icon" / "icon.png"

def show_dock_icon():
    # set after the window starts; set earlier, it gets reset
    if sys.platform == "darwin":
        from AppKit import NSApplication, NSImage
        from PyObjCTools import AppHelper
        image = NSImage.alloc().initWithContentsOfFile_(str(ICON))
        AppHelper.callAfter(NSApplication.sharedApplication().setApplicationIconImage_, image)

# the app's window, once it is open
WINDOW = {}

def on_start():
    show_dock_icon()
    # a see-through window has no shadow by default; give it back, so the window's edge shows
    window = WINDOW.get("main")
    if sys.platform == "darwin" and window and window.native:
        from PyObjCTools import AppHelper
        AppHelper.callAfter(window.native.setHasShadow_, True)

def start_server():
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server

if __name__ == "__main__":
    webview.settings["ALLOW_FILE_URLS"] = False
    server = start_server()
    WINDOW["main"] = webview.create_window(
        config.get("app_name", "Assistant"),
        f"http://{HOST}:{PORT}",
        width=1360,
        height=860,
        min_size=(420, 560),
        background_color="#EEF1F4",
        # the page paints its own background, so Settings can make it see-through
        transparent=True,
    )
    webview.start(on_start)
    server.should_exit = True
