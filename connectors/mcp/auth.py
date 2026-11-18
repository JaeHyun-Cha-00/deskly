import asyncio
import json
import os
import webbrowser
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from config import APP_DIR

TOKENS_DIR = APP_DIR / "mcp"
# the browser comes back here after the user signs in to a server
CALLBACK_PORT = 33418
REDIRECT = f"http://127.0.0.1:{CALLBACK_PORT}/callback"
SIGN_IN_SECONDS = 180

class SignInNeeded(Exception):
    # the saved sign-in stopped working while answering; the user must connect again
    pass

def token_file(name):
    return TOKENS_DIR / f"{name}.json"

def client_file(name):
    # for servers that don't let apps register themselves (GitHub): the OAuth App's id and
    # secret, saved once with `python -m connectors.mcp.save_client NAME`
    return TOKENS_DIR / f"{name}_client.json"

def registered_client(name):
    if not client_file(name).exists():
        return None
    saved = json.loads(client_file(name).read_text())
    return OAuthClientInformationFull(
        client_id=saved["client_id"],
        client_secret=saved["client_secret"],
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="client_secret_post",
    )

class FileTokenStorage:
    # keeps one server's sign-in (its client registration and tokens) in a private file
    def __init__(self, name):
        self.name = name
        self.file = token_file(name)

    def load(self):
        return json.loads(self.file.read_text()) if self.file.exists() else {}

    def save(self, data):
        TOKENS_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(TOKENS_DIR, 0o700)
        self.file.write_text(json.dumps(data))
        os.chmod(self.file, 0o600)

    async def get_tokens(self):
        tokens = self.load().get("tokens")
        return OAuthToken.model_validate(tokens) if tokens else None

    async def set_tokens(self, tokens):
        self.save(self.load() | {"tokens": tokens.model_dump(mode="json")})

    async def get_client_info(self):
        # a hand-registered OAuth App comes first, so Deskly never tries to register itself there
        registered = registered_client(self.name)
        if registered:
            return registered
        info = self.load().get("client")
        return OAuthClientInformationFull.model_validate(info) if info else None

    async def set_client_info(self, client_info):
        self.save(self.load() | {"client": client_info.model_dump(mode="json")})

async def open_browser(url):
    webbrowser.open(url)

async def no_browser(url):
    # while answering, never open a sign-in page by surprise
    raise SignInNeeded("The sign-in for this app expired. Open Connectors and connect it again.")

async def wait_for_callback():
    # a tiny one-time web server on 127.0.0.1 that catches the browser coming back
    found = asyncio.get_running_loop().create_future()

    async def answer(reader, writer):
        request = (await reader.readline()).decode(errors="replace")
        query = parse_qs(urlparse(request.split(" ")[1] if " " in request else "").query)
        body = b"<p style='font-family:sans-serif'>Signed in. You can close this window and go back to Deskly.</p>"
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + body)
        await writer.drain()
        writer.close()
        if "code" in query and not found.done():
            found.set_result((query["code"][0], query.get("state", [None])[0]))
        elif "error" in query and not found.done():
            found.set_exception(PermissionError(f"Sign-in was cancelled ({query['error'][0]})."))

    server = await asyncio.start_server(answer, "127.0.0.1", CALLBACK_PORT)
    try:
        return await asyncio.wait_for(found, SIGN_IN_SECONDS)
    finally:
        server.close()

class JsonTokenProvider(OAuthClientProvider):
    # GitHub's token server answers in form format unless asked for JSON, and the MCP SDK
    # doesn't ask, so its token requests get "Accept: application/json".
    # These are the SDK's internal methods: if an SDK update breaks a sign-in, look here first.
    async def _exchange_token_authorization_code(self, *args, **kwargs):
        request = await super()._exchange_token_authorization_code(*args, **kwargs)
        request.headers["Accept"] = "application/json"
        return request

    async def _refresh_token(self):
        request = await super()._refresh_token()
        request.headers["Accept"] = "application/json"
        return request

def provider(name, url, interactive, scope=None):
    # handles the server's OAuth: finding its sign-in page, registering Deskly, PKCE, refreshing
    return JsonTokenProvider(
        server_url=url,
        client_metadata=OAuthClientMetadata(
            client_name="Deskly",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",
            # ask only for these permissions, not everything the server offers
            scope=scope,
        ),
        storage=FileTokenStorage(name),
        redirect_handler=open_browser if interactive else no_browser,
        callback_handler=wait_for_callback,
        timeout=SIGN_IN_SECONDS,
    )

def is_signed_in(name):
    return bool(FileTokenStorage(name).load().get("tokens"))

def forget(name):
    token_file(name).unlink(missing_ok=True)
