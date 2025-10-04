from django.shortcuts import render
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import Profile
import random


def index(request):
    if request.user.is_authenticated:
        return redirect('boards')
    else:
        return redirect('signIn')


class SignIn(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('boards')
        else:
            return render(request, 'auth.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('boards')

        else:
            response = JsonResponse({"error": "Invalid Credential"})
            response.status_code = 403
            return response


class SignUp(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('boards')
        else:
            return redirect('signIn')

    def post(self, request):
        try:
            username = request.POST['username']
            email = request.POST['email']
            password = request.POST['password']

            user = User.objects.create_user(username, email, password)
            user.save()

            login(request, user)

            n = random.randint(16, 45)
            pf_url = f'/media/users/{n}.jpg'
            pf = Profile(user=user, profile_photo=pf_url)
            pf.save()

            return redirect('boards')

        except:
            response = JsonResponse(
                {"error": "Duplicate User or Server error"})
            response.status_code = 403
            return response


class SignOut(View):
    def get(self, request):
        logout(request)
        return redirect('signIn')


class ProfileView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')
        first_letter = request.user.username[0].upper(
        ) if request.user.username else ""
        return render(request, 'profile.html', {
            "user": request.user,
            "first": first_letter
        })

    def post(self, request):
        user = request.user
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        avatar = request.FILES.get("profile_photo")

        if username:
            user.username = username
        if email:
            user.email = email
        if password:
            user.set_password(password)
        if avatar:
            user.profile.profile_photo = avatar  # предполагаю, что у тебя есть profile model

        user.save()
        user.profile.save()
        return redirect("profile")
