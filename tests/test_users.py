import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.urls import reverse

from users.models import Profile
from users.views import index, SignIn, SignUp, SignOut, ProfileView


class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = Profile.objects.create(user=self.user)

    # ===== INDEX VIEW TESTS =====
    def test_index_authenticated_redirects_to_boards(self):
        """Тест що аутентифікований користувач редіректиться на boards"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('index'))
        self.assertRedirects(response, reverse('boards'))

    def test_index_unauthenticated_redirects_to_signin(self):
        """Тест що неаутентифікований користувач редіректиться на signIn"""
        response = self.client.get(reverse('index'))
        self.assertRedirects(response, reverse('signIn'))

    # ===== SIGNIN VIEW TESTS =====
    def test_signin_get_authenticated_redirects_to_boards(self):
        """Тест GET запиту для аутентифікованого користувача"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('signIn'))
        self.assertRedirects(response, reverse('boards'))

    def test_signin_get_unauthenticated_returns_auth_page(self):
        """Тест GET запиту для неаутентифікованого користувача"""
        response = self.client.get(reverse('signIn'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth.html')

    def test_signin_post_valid_credentials(self):
        """Тест POST запиту з валідними обліковими даними"""
        response = self.client.post(reverse('signIn'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('boards'))

    def test_signin_post_invalid_credentials(self):
        """Тест POST запиту з невірними обліковими даними"""
        response = self.client.post(reverse('signIn'), {
            'username': 'wronguser',
            'password': 'wrongpass'
        })
        self.assertRedirects(response, reverse('signIn'))

        # Перевіряємо повідомлення про помилку
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]), "Invalid username or password.")

    def test_signin_post_empty_credentials(self):
        """Тест POST запиту з порожніми обліковими даними"""
        response = self.client.post(reverse('signIn'), {
            'username': '',
            'password': ''
        })
        self.assertRedirects(response, reverse('signIn'))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]), "Invalid username or password.")

    # ===== SIGNUP VIEW TESTS =====
    def test_signup_get_authenticated_redirects_to_boards(self):
        """Тест GET запиту для аутентифікованого користувача"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('signUp'))
        self.assertRedirects(response, reverse('boards'))

    def test_signup_get_unauthenticated_redirects_to_signin(self):
        """Тест GET запиту для неаутентифікованого користувача"""
        response = self.client.get(reverse('signUp'))
        self.assertRedirects(response, reverse('signIn'))

    def test_signup_post_valid_data(self):
        """Тест POST запиту з валідними даними реєстрації"""
        response = self.client.post(reverse('signUp'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123'
        })
        self.assertRedirects(response, reverse('boards'))

        # Перевіряємо що користувач створений
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue(Profile.objects.filter(
            user__username='newuser').exists())

        # Перевіряємо повідомлення про успіх
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]), "Account created successfully!")

    def test_signup_post_existing_username(self):
        """Тест POST запиту з існуючим іменем користувача"""
        response = self.client.post(reverse('signUp'), {
            'username': 'testuser',  # Вже існує
            'email': 'new@example.com',
            'password': 'newpass123'
        })
        self.assertRedirects(response, reverse('signIn'))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(
            messages_list[0]), "This username is already taken. Please choose another one.")

    def test_signup_post_existing_email(self):
        """Тест POST запиту з існуючою email адресою"""
        response = self.client.post(reverse('signUp'), {
            'username': 'newuser',
            'email': 'test@example.com',  # Вже існує
            'password': 'newpass123'
        })
        self.assertRedirects(response, reverse('signIn'))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]), "An account with this email already exists.")

    def test_signup_post_missing_username(self):
        """Тест POST запиту без імені користувача"""
        response = self.client.post(reverse('signUp'), {
            'username': '',
            'email': 'new@example.com',
            'password': 'newpass123'
        })
        self.assertRedirects(response, reverse('signIn'))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]), "Username and password are required.")

    def test_signup_post_missing_password(self):
        """Тест POST запиту без пароля"""
        response = self.client.post(reverse('signUp'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': ''
        })
        self.assertRedirects(response, reverse('signIn'))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]), "Username and password are required.")

    # ===== SIGNOUT VIEW TESTS =====
    def test_signout_get(self):
        """Тест GET запиту для виходу з системи"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('signOut'))
        self.assertRedirects(response, reverse('signIn'))

        # Перевіряємо що користувач вийшов з системи
        from django.contrib.auth import get_user
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)

        # Перевіряємо повідомлення
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "You have been logged out.")

    # ===== PROFILE VIEW TESTS =====
    def test_profile_get_authenticated(self):
        """Тест GET запиту для аутентифікованого користувача"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

    def test_profile_get_unauthenticated_redirects(self):
        """Тест GET запиту для неаутентифікованого користувача"""
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, reverse('signIn'))

    def test_profile_get_creates_profile_if_missing(self):
        """Тест що профіль створюється якщо відсутній"""
        # Видаляємо профіль
        Profile.objects.filter(user=self.user).delete()

        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))

        # Перевіряємо що профіль був створений
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
        self.assertEqual(response.status_code, 200)

    def test_profile_post_avatar_upload(self):
        """Тест POST запиту з завантаженням аватара"""
        self.client.force_login(self.user)

        # Створюємо тестовий файл
        avatar_file = SimpleUploadedFile(
            "test_avatar.jpg",
            b"file_content",
            content_type="image/jpeg"
        )

        response = self.client.post(reverse('profile'), {
            'profile_photo': avatar_file
        })

        self.assertRedirects(response, reverse('profile'))

        # Оновлюємо профіль з бази даних
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.profile_photo)

        # Перевіряємо повідомлення про успіх
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Профіль успішно оновлено.", str(messages_list[0]))

    def test_profile_post_update_username(self):
        """Тест POST запиту для оновлення імені користувача"""
        self.client.force_login(self.user)

        response = self.client.post(reverse('profile'), {
            'username': 'newusername',
            'email': self.user.email,
            'password': ''
        })

        self.assertRedirects(response, reverse('profile'))

        # Оновлюємо користувача з бази даних
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newusername')

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Профіль успішно оновлено.", str(messages_list[0]))

    def test_profile_post_update_email(self):
        """Тест POST запиту для оновлення email"""
        self.client.force_login(self.user)

        response = self.client.post(reverse('profile'), {
            'username': self.user.username,
            'email': 'newemail@example.com',
            'password': ''
        })

        self.assertRedirects(response, reverse('profile'))

        # Оновлюємо користувача з бази даних
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Профіль успішно оновлено.", str(messages_list[0]))

    def test_profile_post_existing_username(self):
        """Тест POST запиту з існуючим іменем користувача"""
        # Створюємо іншого користувача
        other_user = User.objects.create_user(
            username='existinguser',
            email='other@example.com',
            password='otherpass123'
        )

        self.client.force_login(self.user)
        response = self.client.post('/profile/', {
            'username': 'existinguser',  # Вже існує
            'email': self.user.email,
            'password': ''
        })

        # При помилці валідації маємо залишитися на сторінці профілю (status 200)
        # або бути редіректнуті назад на профіль
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertEqual(response.url, '/profile/')

        # Шукаємо конкретне повідомлення про помилку
        messages_list = list(messages.get_messages(response.wsgi_request))
        error_messages = [
            msg for msg in messages_list if "Користувач з таким ім'ям вже існує" in str(msg)]

        # Має бути хоча б одне повідомлення про помилку
        self.assertTrue(len(error_messages) >= 1)

        # Перевіряємо що ім'я не змінилося
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')  # Початкове ім'я

    def test_profile_post_existing_email(self):
        """Тест POST запиту з існуючою email адресою"""
        # Створюємо іншого користувача
        other_user = User.objects.create_user(
            username='otheruser',
            email='existing@example.com',
            password='otherpass123'
        )

        self.client.force_login(self.user)
        response = self.client.post('/profile/', {
            'username': self.user.username,
            'email': 'existing@example.com',  # Вже існує
            'password': ''
        })

        # При помилці валідації маємо залишитися на сторінці профілю (status 200)
        # або бути редіректнуті назад на профіль
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertEqual(response.url, '/profile/')

        # Шукаємо конкретне повідомлення про помилку серед усіх повідомлень
        messages_list = list(messages.get_messages(response.wsgi_request))
        error_messages = [
            msg for msg in messages_list if "Користувач з таким email вже існує" in str(msg)]

        # Має бути хоча б одне повідомлення про помилку
        self.assertTrue(len(error_messages) >= 1,
                        f"Не знайдено повідомлення про помилку. Усі повідомлення: {[str(msg) for msg in messages_list]}")

        # Перевіряємо що email не змінився
        self.user.refresh_from_db()
        # Початковий email
        self.assertEqual(self.user.email, 'test@example.com')

    def test_profile_post_unauthenticated_redirects(self):
        """Тест POST запиту для неаутентифікованого користувача"""
        response = self.client.post(reverse('profile'), {
            'username': 'newusername',
            'email': 'new@example.com',
            'password': 'newpass123'
        })
        self.assertRedirects(response, reverse('signIn'))

    def test_profile_post_empty_username_not_allowed(self):
        """Тест POST запиту з порожнім іменем користувача"""
        self.client.force_login(self.user)

        response = self.client.post(reverse('profile'), {
            'username': '',  # Порожнє ім'я
            'email': self.user.email,
            'password': ''
        })

        self.assertRedirects(response, reverse('profile'))

        # Ім'я не повинно змінитися
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Профіль успішно оновлено.", str(messages_list[0]))
