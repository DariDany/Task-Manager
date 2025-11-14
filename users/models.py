from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Адмін"
        EMPLOYEE = "EMPLOYEE", "Співробітник"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(
        upload_to="profiles/",
        default="profiles/default.jpg"
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,   # за замовчуванням – співробітник
    )

    def __str__(self):
        return self.user.username

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE
