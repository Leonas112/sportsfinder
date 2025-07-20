from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm
from django import forms



# Create your views here.
def login_view(request, *args, **kwargs):
    if request.method == 'POST':
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to a success page.
            return redirect('home')
        else:
            messages.success(request, ('There was an error logging in :('))
            return redirect('login')
    else:
        return render(request, "authenticate/login.html", {})
    #return HttpResponse("<h1>Hello World </h1>")


def logout_view(request, *args, **kwargs):
    logout(request)
    messages.success(request, ('You Were Logged Out.'))
    return redirect("home")


def register_view(request, *args, **kwargs):
    form = SignUpForm()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            #login user
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, ('Registration was succesfull'))
            return redirect('home')
        else:
            messages.success(request, ('Whoops! There was a problem registration, please try again.'))
            return redirect('register')

    else:
        return render(request, "authenticate/register.html", {'form':form})