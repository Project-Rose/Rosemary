from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from db.models import User
import requests
import os
import json
import random
import string

# Create your views here.

def index(request):
    return render(request, "index.html")

def auth(request):
    if request.GET.get("code"):
        req = requests.post("https://discord.com/api/v10/oauth2/token", {"client_id": os.getenv("DISCORD_CLIENT_ID"), "client_secret": os.getenv("DISCORD_CLIENT_SECRET"), "grant_type": "authorization_code", "code": request.GET.get("code"), "redirect_uri": request.build_absolute_uri("/auth")})
        if req.status_code != 200:
            return HttpResponse("Failed to authenticate. Please try again.")
        response = json.loads(req.content)
        req = requests.get("https://discord.com/api/v10/oauth2/@me", headers={"Authorization": "Bearer "+response["access_token"]})
        if req.status_code != 200:
            return HttpResponse("Failed to authenticate. Please try again.")
        response = json.loads(req.content)
        try:
            user = User.objects.get(discord_id=response["user"]["id"])
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect("/")
            else:
                return HttpResponse("Account not activated. To activate your account, go on the Project Rosé discord, and type /activate code:"+user.code)
        except User.DoesNotExist:
            user = User.objects.create_superuser(username=response["user"]["username"],discord_id=response["user"]["id"],is_active=False,code=''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(17)))
            return HttpResponse("Sucessfully authenticated. To activate your account, go on the Project Rosé discord, and type /activate code:"+user.code)
    else:
        return HttpResponseForbidden()


def err404(request, exception):
    return render(request, "404.html", {"title": "404!!!!!!"})

def err500(request):
    return render(request, "500.html", {"title": "😍"})