import asyncio
import threading

# One event loop for the whole app, in its own thread. Network connections (the model,
# MCP servers) belong to the loop they were made on, so all async work must use this one.
LOOP = asyncio.new_event_loop()
threading.Thread(target=LOOP.run_forever, name="event-loop", daemon=True).start()

def run(coroutine, timeout=None):
    # runs async work on the app's loop from normal code, and waits for its result
    return asyncio.run_coroutine_threadsafe(coroutine, LOOP).result(timeout)
