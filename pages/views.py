from django.http import HttpResponse
from django.shortcuts import render 
# Create your views here.
def home_view(request, *args, **kwargs):
    return render(request, "home.html", {})
    #return HttpResponse("<h1>Hello World </h1>")


def search_view(request, *args, **kwargs):
    return render(request, "search.html", {})