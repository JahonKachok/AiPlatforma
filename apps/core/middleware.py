class DarkModeMiddleware:
    """Reads the ``dark_mode`` cookie so templates can render the right theme
    class on the very first response (no flash-of-wrong-theme on load)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.dark_mode = request.COOKIES.get("dark_mode", "1") == "1"
        return self.get_response(request)
