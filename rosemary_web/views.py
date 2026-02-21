from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from db.models import User
import requests
import os
import json
import random
import string

# Create your views here.

def index(request):
    if request.user.is_authenticated:
        return render(request, "index.html", {"title": "Home"})
    else:
        return render(request, "login.html", {"title": "Login", "discord_url": f"https://discord.com/oauth2/authorize?client_id={os.getenv("DISCORD_CLIENT_ID")}&response_type=code&redirect_uri={request.build_absolute_uri("/auth")}&scope=identify"})

def auth(request):
    if request.GET.get("code"):
        req = requests.post("https://discord.com/api/v10/oauth2/token", {"client_id": os.getenv("DISCORD_CLIENT_ID"), "client_secret": os.getenv("DISCORD_CLIENT_SECRET"), "grant_type": "authorization_code", "code": request.GET.get("code"), "redirect_uri": request.build_absolute_uri("/auth")})
        if req.status_code != 200:
            return HttpResponse("Failed to authenticate. Please try again.")
        response = json.loads(req.content)
        req = requests.get("https://discord.com/api/v10/oauth2/@me", headers={"Authorization": f"Bearer {response["access_token"]}"})
        if req.status_code != 200:
            return HttpResponse("Failed to authenticate. Please try again.")
        response = json.loads(req.content)
        try:
            user = User.objects.get(discord_id=response["user"]["id"])
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect("/")
            else:
                return HttpResponse(f"Account not activated. To activate your account, go on the Project Rosé discord, and type /activate code:{user.code}")
        except User.DoesNotExist:
            user = User.objects.create_superuser(username=response["user"]["username"],discord_id=response["user"]["id"],is_active=False,code=''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(17)))
            return HttpResponse(f"Sucessfully authenticated. To activate your account, go on the Project Rosé discord, and type /activate code:{user.code}")
    else:
        return HttpResponseForbidden()

def signout(request):
    logout(request)
    return HttpResponseRedirect("/")

def err404(request, exception):
    return render(request, "404.html", {"title": "404!!!!!!"})

def err500(request):
    return render(request, "500.html", {"title": "😍"})