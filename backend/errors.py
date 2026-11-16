from connectors.apps import APPS

FRIENDLY_ERRORS = {
    "AuthenticationError": "OpenRouter didn't accept the API key. Check OPENROUTER_API_KEY in .env, then restart the app.",
    "OpenAIError": "The OpenRouter API key is missing. Add OPENROUTER_API_KEY to .env, then restart the app.",
    "RateLimitError": "OpenRouter is busy or your credits ran out. Wait a moment and try again, or check your credits.",
    "APIConnectionError": "Couldn't reach OpenRouter. Check the internet connection and try again.",
    "APITimeoutError": "OpenRouter took too long to answer. Try again.",
    # 5xx: the model's server is starting up or having trouble
    "InternalServerError": "The model isn't available right now. Wait a minute and try again.",
    "NotFoundError": "OpenRouter doesn't know this model. Check the model name in config.yaml.",
    "RefreshError": "Your Google sign-in expired. Open Connectors and connect your apps again.",
    "HttpError": "Google answered with an error. Try again in a moment.",
}

def error_name(error):
    # LangChain renames OpenAI's errors (RateLimitError becomes OpenAIRateLimitError),
    # so look at the parent classes too, but stop before the general ones
    for cls in type(error).__mro__:
        if cls.__name__ in FRIENDLY_ERRORS:
            return cls.__name__
        if cls.__name__ in ("APIError", "Exception"):
            break
    return type(error).__name__

def friendly_error(error):
    name = error_name(error)
    if name == "RefreshError":
        # a saved sign-in no longer works, and the error doesn't say which app's
        for client in APPS.values():
            client.sign_out()
    return FRIENDLY_ERRORS.get(name, str(error))
