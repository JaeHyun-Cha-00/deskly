from config import ADDRESS

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; "
        "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-cache",
}

def from_our_page(request):
    # other websites open in the browser must not be able to use this app's API
    if request.headers.get("host") != ADDRESS:
        return False
    if not request.url.path.startswith("/api/"):
        return True
    origin = request.headers.get("origin", f"http://{ADDRESS}")
    return origin == f"http://{ADDRESS}" and request.headers.get("x-assistant") == "1"
