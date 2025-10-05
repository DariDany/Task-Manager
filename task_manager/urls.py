from django.urls import path
from .views import (
    Projects, Tasks, ManageTasks, ManageProject,
    MyTasksAll, ToggleTask, SetTaskStatus,
)

urlpatterns = [
    path('', Projects.as_view(), name='boards'),

    # спочатку фіксований шлях на «мої завдання»
    path('my-tasks/', MyTasksAll.as_view(), name='my_tasks_all'),
    path('tasks/toggle/<int:id>/', SetTaskStatus.as_view(), name='toggle_task'),    # keep old name working
    path('tasks/set-status/<int:id>/', SetTaskStatus.as_view(), name='set_task_status'),  # new, explicit

    # перемикач статусу (DONE/TO DO)
    path('tasks/toggle/<int:id>/', ToggleTask.as_view(), name='toggle_task'),

    # ДАЛІ — усі проєктні шляхи тільки з int-конвертерами
    path('<int:id>/', Tasks.as_view(), name='tasks'),
    path('<int:id>/delete', ManageProject.as_view()),
    path('<int:id>/task', ManageTasks.as_view()),
]
