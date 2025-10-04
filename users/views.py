from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from .models import Profile


def index(request):
    if request.user.is_authenticated:
        return redirect('boards')
    else:
        return redirect('signIn')


class SignIn(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('boards')
        return render(request, 'auth.html')

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('boards')

        messages.error(request, "Invalid username or password.")
        return redirect('signIn')


class SignUp(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('boards')
        return redirect('signIn')

    @transaction.atomic
    def post(self, request):
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        password = (request.POST.get('password') or '')

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect('signIn')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "This username is already taken. Please choose another one.")
            return redirect('signIn')

        if email and User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('signIn')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('boards')

        except IntegrityError:
            messages.error(request, "A user with these details already exists.")
            return redirect('signIn')
        except Exception:
            messages.error(request, "An error occurred during registration. Please try again.")
            return redirect('signIn')


class SignOut(View):
    def get(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('signIn')


class ProfileView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        first_letter = request.user.username[0].upper() if request.user.username else ""
        return render(request, 'profile.html', {"user": request.user, "first": first_letter})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        User = get_user_model()
        user = request.user

        new_username = request.POST.get("username", "").strip()
        new_email = request.POST.get("email", "").strip()
        new_password = request.POST.get("password", "")
        avatar = request.FILES.get("profile_photo")

        # Check username uniqueness (excluding current user)
        if new_username and new_username != user.username:
            if User.objects.filter(username__iexact=new_username).exclude(pk=user.pk).exists():
                messages.error(request, "This username is already in use.")
                return redirect("profile")
            user.username = new_username

        # Check email uniqueness (excluding current user)
        if new_email and new_email.lower() != (user.email or "").lower():
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                messages.error(request, "An account with this email already exists.")
                return redirect("profile")
            user.email = new_email

        password_changed = False
        if new_password:
            user.set_password(new_password)
            password_changed = True

        if avatar:
            user.profile.profile_photo = avatar

        user.save()
        user.profile.save()

        if password_changed:
            update_session_auth_hash(request, user)

        messages.success(request, "Profile updated successfully.")
        return redirect("boards")
