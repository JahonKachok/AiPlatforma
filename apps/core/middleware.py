from django.http import HttpResponsePermanentRedirect


class WwwRedirectMiddleware:
    """``www.example.com`` -> ``example.com`` with a permanent redirect.

    Keeps a single canonical host, so sessions, CSRF cookies and search
    indexing are not split across two names. The host comes from
    ``request.get_host()``, which Django has already checked against
    ALLOWED_HOSTS — the redirect target is only ever that host minus "www.",
    so this cannot be abused as an open redirect.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if host.lower().startswith("www."):
            target = f"{request.scheme}://{host[4:]}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(target)
        return self.get_response(request)


class DarkModeMiddleware:
    """Reads the ``dark_mode`` cookie so templates can render the right theme
    class on the very first response (no flash-of-wrong-theme on load)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.dark_mode = request.COOKIES.get("dark_mode", "1") == "1"
        return self.get_response(request)
