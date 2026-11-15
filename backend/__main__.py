import threading
import webbrowser

import uvicorn

from backend.server import app
from config import HOST, PORT

if __name__ == "__main__":
    url = f"http://{HOST}:{PORT}"
    threading.Timer(1.0, webbrowser.open, args=[url]).start()
    print(f"Open {url}  (Ctrl+C to stop)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
