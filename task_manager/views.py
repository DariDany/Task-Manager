import datetime
import json
import random

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View

from reports.models import ProjectInfo
from .models import Task, Project
from users.models import Profile
from django.urls import reverse

def user_is_admin(user):
    """
    Повертає True, якщо у користувача глобальна роль ADMIN.
    Використовується на сторінці 'My tasks' та в інших місцях.
    """
    try:
        return hasattr(user, "profile") and user.profile.role == Profile.Role.ADMIN
    except Profile.DoesNotExist:
        return False
def is_admin_for_project(user, project):
    """
    Користувач вважається адміном, якщо:
    - має роль ADMIN у профілі, АБО
    - є власником конкретного проекту.
    """
    try:
        # глобальна роль
        if hasattr(user, "profile") and getattr(user.profile, "role", None) == "ADMIN":
            return True
    except Exception:
        # на випадок, якщо профілю нема
        pass

    # адмін проєкту (старе правило з оригінального коду)
    return project.owner_id == user.id



class Projects(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        projects = Project.objects.all()
        list = []

        for p in projects:
            if p.owner == user or user.id in p.get_members():
                list.append(ProjectInfo(p))

        data = {"user": user,
                "first": user.username[0],
                "other_users": User.objects.filter(~Q(id=user.id)).all(),
                "projects": list,
                }
        return render(request, 'projects.html', data)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        name = request.POST['name']
        description = request.POST['desc']
        details = request.POST['details']
        owner = request.user
        user_ids = request.POST.getlist('users', [])

        ids = []
        for id in user_ids:
            ids.append(int(id))

        n = random.randint(1, 7)
        pf_url = f'/media/project-logos/{n}.png'

        proj = Project.objects.create(name=name, description=description, details=details, owner=owner,
                                      members=json.dumps(ids), profile_photo=pf_url)
        proj.save()

        return redirect('boards')


class ManageProject(View):
    def post(self, request, id):
        Project.objects.filter(id=id).delete()

        response = JsonResponse({"message": "OK"})
        response.status_code = 200
        return response


class Tasks(View):
    def get(self, request, id):
        if not request.user.is_authenticated:
            return redirect("signIn")

        proj = Project.objects.filter(id=id).first()
        user = request.user
        users = User.objects.filter(
            Q(id__in=proj.get_members()) | Q(id=proj.owner.id))
        tasks = proj.task_set.all()
        data = {"user": user,
                "first": user.username[0],
                "other_users": users,
                "tasks": tasks,
                "other_tasks": tasks,
                'proj': proj,
                "can_add": user == proj.owner
                }
        return render(request, 'tasks.html', data)

    def post(self, request, id):
        if not request.user.is_authenticated:
            return redirect('signIn')

        name = request.POST['name']
        description = request.POST['desc']
        assigned_to = request.POST['users']
        status = 'T'
        start_time = request.POST.get('start_time')
        end_time = request.POST['date']
        predecessor_id = request.POST.get('predecessor')

        task = Task(name=name, description=description, assigned_to_id=assigned_to, status=status, start_time=start_time,
                    end_time=end_time, project_id=id)
        task.save()
        # Якщо обрано попередника — зберігаємо зв’язок
        if predecessor_id and predecessor_id != "none":
            predecessor_task = Task.objects.filter(id=predecessor_id).first()
            if predecessor_task:
                task.predecessor = predecessor_task
                task.save()

        return redirect('tasks', id=id)


class ManageTasks(View):
    def post(self, request, id):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Invalid User"}, status=403)

        type_ = request.POST.get("type")

        # ---- ДЛЯ AJAX-перевірки доступу з Kanban ----
        if type_ == "check_access":
            task_id = request.POST.get("task_id")
            task = (
                Task.objects
                .select_related("project", "assigned_to")
                .filter(id=task_id)
                .first()
            )
            if not task:
                return JsonResponse({"allowed": False, "error": "Task Not Found"}, status=404)

            admin_for_project = is_admin_for_project(request.user, task.project)
            allowed = admin_for_project or (task.assigned_to_id == request.user.id)

            return JsonResponse({"allowed": allowed})

        # далі йде твій старий код з type_ == 'edit_status' / 'edit_end_time'
        user = request.user

        # ---------------- type == edit_status (drag & drop на дошці) ----------------
        if type_ == 'edit_status':
            task_id = request.POST.get('task_id')
            new_status = request.POST.get('board_id')  # колонка, куди перетягнули

            task = (
                Task.objects
                .select_related('project', 'assigned_to')
                .filter(id=task_id)
                .first()
            )
            if not task:
                return JsonResponse({"error": "Task Not Found"}, status=404)

            admin_for_project = is_admin_for_project(user, task.project)

            # Колонки, які можуть міняти тільки адміни (Done/Blocked/Deleted)
            if new_status in ['O', 'B', 'L'] or task.status in ['O', 'B', 'L']:
                if not admin_for_project:
                    return JsonResponse({"error": "You Do Not Have Permission"}, status=403)

                task.status = new_status
                task.save()
            else:
                # Інші статуси (T, D, I...) – може змінювати:
                # - виконавець задачі, АБО
                # - адмін (глобальний чи власник проєкту)
                if task.assigned_to_id != user.id and not admin_for_project:
                    return JsonResponse({"error": "You Do Not Have Permission"}, status=403)

                task.status = new_status

                if new_status == 'D' and not task.start_time:
                    task.start_time = datetime.datetime.today().date()

                task.save()

            return JsonResponse({"message": "OK"}, status=200)

        # ---------------- type == edit_end_time (drag в календарі) ----------------
        if type_ == 'edit_end_time':
            task_id = request.POST.get('task_id')
            end_time = request.POST.get('new_end_time')

            task = (
                Task.objects
                .select_related('project')
                .filter(id=task_id)
                .first()
            )
            if not task:
                return JsonResponse({"error": "Task Not Found"}, status=404)

            admin_for_project = is_admin_for_project(user, task.project)

            if not admin_for_project:
                return JsonResponse({"error": "You Do Not Have Permission"}, status=403)

            task.end_time = end_time
            task.save()

            return JsonResponse({"message": "OK"}, status=200)

        return JsonResponse({"error": "Invalid Request Type"}, status=400)


            
class MyTasksAll(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        tasks = (
            Task.objects
                .select_related('project')
                .filter(assigned_to=request.user)
                .order_by('status', 'end_time', 'project__name', 'id')
        )
        ctx = {"user": request.user, "first": request.user.username[0], "tasks": tasks}
        return render(request, 'my_tasks_all.html', ctx)
    
class ToggleTask(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        is_admin = user_is_admin(user)

        task_id = request.POST.get('task_id')
        next_url = request.POST.get('next', 'my_tasks_all')

        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            messages.error(request, "Задачу не знайдено.")
            return redirect(next_url)

        # 🔐 ДОСТУП:
        #  - адмін: може змінювати будь-яку задачу
        #  - співробітник: тільки якщо він виконавець цієї задачі
        if not is_admin and task.assigned_to != user:
            messages.error(request, "Ви можете змінювати тільки власні задачі.")
            return redirect(next_url)

        # далі – твоя стара логіка перемикання статусу (T <-> O або щось подібне)
        if task.status == 'T':
            task.status = 'O'
        else:
            task.status = 'T'

        task.save()

        return redirect(next_url)
    
class SetTaskStatus(View):
    ALLOWED = {'T', 'D', 'I', 'O'}   # як у тебе було

    def post(self, request, id):
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        is_admin = user_is_admin(user)

        # У тебе в POST зараз поле називається new_status, а не status
        status = request.POST.get('status') or request.POST.get('new_status')
        next_url = request.POST.get('next', 'my_tasks_all')

        if status not in self.ALLOWED:
           messages.error(request, "Invalid task status.")
           return redirect(next_url)

        # беремо task_id з POST, а якщо його немає – з URL (id)
        task_id = request.POST.get('task_id') or id

        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            messages.error(request, "The task is not found.")
            return redirect(next_url)

        # 🔐 ДОСТУП:
        if not is_admin and task.assigned_to != user:
            messages.error(request, "You do not have permission to modify another employee's task.")
            return redirect(next_url)

        old_status = task.status
        task.status = status

        if status == 'D' and task.start_time is None:
            from datetime import datetime
            task.start_time = datetime.now()
        if status == 'T':
            task.start_time = None

        task.save()

        return redirect(next_url)
