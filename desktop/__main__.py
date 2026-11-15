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

def start_server():
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server

if __name__ == "__main__":
    webview.settings["ALLOW_FILE_URLS"] = False
    server = start_server()
    webview.create_window(
        config.get("app_name", "Assistant"),
        f"http://{HOST}:{PORT}",
        width=1360,
        height=860,
        min_size=(420, 560),
        background_color="#EEF1F4",
    )
    webview.start(show_dock_icon)
    server.should_exit = True
