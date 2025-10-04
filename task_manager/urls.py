from django.urls import path
from .views import Projects, Tasks, ManageTasks, ManageProject

urlpatterns = [
    path('', Projects.as_view(), name='boards'),
    path('<id>', Tasks.as_view(), name='tasks'),
    path('<id>/delete', ManageProject.as_view()),
    path('<id>/task', ManageTasks.as_view())
]
