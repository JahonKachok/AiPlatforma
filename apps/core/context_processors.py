def dark_mode(request):
    return {"dark_mode": getattr(request, "dark_mode", True)}
