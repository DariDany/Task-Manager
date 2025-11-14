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

        # 👇 Гарантуємо, що у користувача є Profile
        Profile.objects.get_or_create(user=request.user)

        return render(request, 'profile.html', {})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        # 👇 тут теж гарантуємо наявність Profile
        profile, created = Profile.objects.get_or_create(user=user)

        avatar = request.FILES.get('profile_photo')
        if avatar:
            profile.profile_photo = avatar
            profile.save()

        new_username = request.POST.get('username', '').strip()
        new_email = request.POST.get('email', '').strip()
        new_password = request.POST.get('password', '').strip()

        # 🔹 username – не даємо зробити порожнім
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                messages.error(request, "Користувач з таким ім'ям вже існує.")
            else:
                user.username = new_username

        # 🔹 email – опціональний, але якщо не порожній, то перевіряємо унікальність
        if new_email != user.email:
            if new_email and User.objects.filter(email=new_email).exclude(id=user.id).exists():
                messages.error(request, "Користувач з таким email вже існує.")
            else:
                user.email = new_email

        # 🔹 пароль – тільки якщо щось ввели
        if new_password:
            user.set_password(new_password)

        user.save()

        messages.success(request, "Профіль успішно оновлено.")
        return redirect('profile')