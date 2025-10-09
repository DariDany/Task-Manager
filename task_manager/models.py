from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import datetime
import json


class Project(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    details = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    members = models.CharField(max_length=500)
    profile_photo = models.CharField(
        max_length=200, default='/static/media/project-logos/1.png')

    def get_members(self):
        return json.loads(self.members)


class Task(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)
    status_choices = (
        ('T', 'To Do'),
        ('D', 'Doing'),
        ('I', 'In Test'),
        ('O', 'Done'),
        ('B', 'Blocked'),
        ('L', 'Deleted')
    )
    status = models.CharField(max_length=1, choices=status_choices)
    start_time = models.DateField(null=True)
    end_time = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    # 👇 нове поле:
    predecessor = models.ForeignKey(
        'self',                     # посилання на інший Task
        on_delete=models.SET_NULL,  # якщо попередник видалений, то null
        null=True,                  # дозволяє бути порожнім
        blank=True,                 # дозволяє залишати поле пустим у формах
        related_name='followers'    # для зворотного доступу (необов’язково)
    )

    def __str__(self):
        return self.name
