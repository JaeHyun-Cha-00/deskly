from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.routes import chats, connectors, status
from backend.security import SECURITY_HEADERS, from_our_page

FRONTEND = Path(__file__).parent.parent / "frontend"

app = FastAPI()
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
app.include_router(status.router)
app.include_router(connectors.router)
app.include_router(chats.router)

@app.middleware("http")
async def only_our_page(request: Request, call_next):
    if not from_our_page(request):
        return JSONResponse({"detail": "This app only accepts requests from its own page."}, status_code=403)
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response

@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")
