from connectors.gmail.client import sign_out

FRIENDLY_ERRORS = {
    "AuthenticationError": "DeepInfra didn't accept the API key. Check DEEPINFRA_API_KEY in .env, then restart the app.",
    "OpenAIError": "The DeepInfra API key is missing. Add DEEPINFRA_API_KEY to .env, then restart the app.",
    "RateLimitError": "DeepInfra is busy or the usage limit was reached. Wait a moment and try again.",
    "APIConnectionError": "Couldn't reach DeepInfra. Check the internet connection and try again.",
    "APITimeoutError": "DeepInfra took too long to answer. Try again.",
    "NotFoundError": "DeepInfra doesn't know this model. Pick another one in Settings.",
    "RefreshError": "Your Gmail sign-in expired. Open Connectors and connect Gmail again.",
    "HttpError": "Gmail answered with an error. Try again in a moment.",
}

def friendly_error(error):
    name = type(error).__name__
    if name == "RefreshError":
        # the saved sign-in no longer works
        sign_out()
    return FRIENDLY_ERRORS.get(name, str(error))
