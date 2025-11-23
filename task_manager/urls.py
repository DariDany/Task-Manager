from django.urls import path
from .views import (
    Projects, Tasks, ManageTasks, ManageProject,
    MyTasksAll, ToggleTask, SetTaskStatus,
)

urlpatterns = [
    # Головна сторінка модуля — список всіх проєктів (дошок).
    path('', Projects.as_view(), name='boards'),

    # Сторінка з усіма задачами, призначеними поточному користувачу.
    path('my-tasks/', MyTasksAll.as_view(), name='my_tasks_all'),
    # Використовується SetTaskStatus, щоб підтримати старий URL /tasks/toggle/<id>/ (для зворотної сумісності).
    path('tasks/toggle/<int:id>/', SetTaskStatus.as_view(), name='toggle_task'),
    # Викликає той самий SetTaskStatus, але під новим ім'ям.
    path('tasks/set-status/<int:id>/',
         SetTaskStatus.as_view(), name='set_task_status'),
    # перемикач статусу (DONE/TO DO)
    path('tasks/toggle/<int:id>/', ToggleTask.as_view(), name='toggle_task'),
    # Список задач конкретного проєкту.
    path('<int:id>/', Tasks.as_view(), name='tasks'),
    # Видалення проєкту.
    path('<int:id>/delete', ManageProject.as_view()),
    # Створення/редагування задач у межах проєкту.
    path('<int:id>/task', ManageTasks.as_view()),
]
