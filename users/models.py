from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    class Role(models.TextChoices):
        # Доступні ролі користувачів, які будуть відображатися у вигляді select у формах.
        # ADMIN — адміністратор, EMPLOYEE — звичайний співробітник.
        ADMIN = "ADMIN", "Адмін"
        EMPLOYEE = "EMPLOYEE", "Співробітник"

    # Зв'язок 1-до-1 з базовою Django-моделлю User.
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Фото профілю користувача.
    profile_photo = models.ImageField(
        upload_to="profiles/",  # шлях, куди будуть зберігатися зображення.
        # стандартне фото, якщо користувач не завантажив власне.
        default="profiles/default.jpg"
    )
    # Поле для визначення ролі користувача.
    role = models.CharField(
        max_length=20,
        choices=Role.choices,  # обмежує можливі значення до списку Role.
        default=Role.EMPLOYEE,   # за замовчуванням – співробітник
    )

    # Повертає ім'я користувача при виведенні об'єкта Profile у адмінці або консолі.
    def __str__(self):
        return self.user.username

    # повертає True, якщо користувач є адміністратором.
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    # повертає True, якщо користувач — співробітник.
    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE
