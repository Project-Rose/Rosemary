from django.http import HttpResponseRedirect, HttpRequest
import os

class RosemaryWebMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        return response
    def process_view(self, request: HttpRequest, view_func, view_args, view_kwarg):
        if not request.user.is_authenticated and request.path != "/auth":
            return HttpResponseRedirect("https://discord.com/oauth2/authorize?client_id="+os.getenv("DISCORD_CLIENT_ID")+"&response_type=code&redirect_uri="+request.build_absolute_uri("/auth")+"&scope=identify")
        return