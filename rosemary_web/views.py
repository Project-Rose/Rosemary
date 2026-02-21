from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.models import User

# Create your views here.

def index(request):
    return render(request, "index.html")

def auth(request):
    if request.GET.get("code"):
        return HttpResponse("the code was: "+request.GET.get("code"))
    else:
        return HttpResponseForbidden()


def err404(request, exception):
    return render(request, "404.html", {"title": "404!!!!!!"})

def err500(request):
    return render(request, "500.html", {"title": "😍"})