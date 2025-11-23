import datetime
import json
import random

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

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
        #  1) Перевірка, що користувач взагалі залогінений
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Invalid User"}, status=403)

        #  2) Шукаємо проєкт
        project = Project.objects.filter(id=id).first()
        if not project:
            return JsonResponse({"error": "Project Not Found"}, status=404)

        #  3) Право на видалення мають:
        #   - глобальний адмін (user_is_admin)
        #   - власник цього проєкту
        if not (user_is_admin(request.user) or project.owner_id == request.user.id):
            return JsonResponse(
                {"error": "You do not have permission to delete this project."},
                status=403
            )

        #  4) Якщо все ОК — видаляємо
        project.delete()
        return JsonResponse({"message": "OK"}, status=200)


class Tasks(View):
    def get(self, request, id):
        # Якщо користувач не авторизований — перенаправляємо на сторінку входу.
        if not request.user.is_authenticated:
            return redirect("signIn")
        # Отримуємо проект з бази даних за його ID.
        proj = Project.objects.filter(id=id).first()
        user = request.user
        # Отримуємо список користувачів, які можуть бути виконавцями задач:
        users = User.objects.filter(
            Q(id__in=proj.get_members()) | Q(id=proj.owner.id))
        # Всі задачі, що належать даному проекту
        tasks = proj.task_set.all()
        # Контекст, який передається в шаблон tasks.html
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

        # Отримуємо дані нової задачі з форми.
        name = request.POST['name']
        description = request.POST['desc']
        assigned_to = request.POST['users']
        status = 'T'  # нова задача завжди створюється у статусі "To Do"
        start_time = request.POST.get('start_time')
        end_time = request.POST['date']
        # ID залежної задачі (якщо вибрано)
        predecessor_id = request.POST.get('predecessor')

        # Створення нової задачі.
        task = Task(name=name, description=description, assigned_to_id=assigned_to, status=status, start_time=start_time,
                    end_time=end_time, project_id=id)
        task.save()
        # Якщо вибрали попередника — прив'язуємо його.
        # Перевіряємо, що вибрано не "none" і що задача існує.
        if predecessor_id and predecessor_id != "none":
            predecessor_task = Task.objects.filter(id=predecessor_id).first()
            if predecessor_task:
                task.predecessor = predecessor_task
                task.save()

        return redirect('tasks', id=id)


class ManageTasks(View):
    def post(self, request, id):
        # Перевірка авторизації: якщо користувач не увійшов — повертаємо помилку 403.
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Invalid User"}, status=403)
        # Отримуємо тип операції з POST-запиту.
        type_ = request.POST.get("type")

        # ДЛЯ AJAX-перевірки доступу з Kanban
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

            # Користувач може змінювати задачу, якщо:
            # - він адміністратор проекту, або
            # - він виконавець задачі
            admin_for_project = is_admin_for_project(
                request.user, task.project)
            allowed = admin_for_project or (
                task.assigned_to_id == request.user.id)

            return JsonResponse({"allowed": allowed})

        # обробка змін задач
        user = request.user

        # drag & drop на дошці
        if type_ == 'edit_status':
            task_id = request.POST.get('task_id')
            # колонка, куди перетягнули
            new_status = request.POST.get('board_id')

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
                # Якщо новий статус – 'Doing' і старт часу ще не встановлений
                if new_status == 'D' and not task.start_time:
                    task.start_time = datetime.datetime.today().date()

                task.save()

            return JsonResponse({"message": "OK"}, status=200)

        # drag & drop в календарі
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
        # Якщо користувач не авторизований — переспрямовуємо його на сторінку логіну.
        if not request.user.is_authenticated:
            return redirect('signIn')

        # Отримуємо всі завдання, призначені поточному користувачу.
        tasks = (
            Task.objects
            # оптимізація запиту, щоб не робити додаткових SQL для project.
            .select_related('project')
            # беремо лише завдання цього користувача.
            .filter(assigned_to=request.user)
            # сортуємо за статусом, дедлайном, назвою проекту та ID.
            .order_by('status', 'end_time', 'project__name', 'id')
        )
        # Формуємо контекст для шаблону.
        ctx = {"user": request.user,
               # перша літера імені користувача (наприклад, для аватара з ініціалами).
               "first": request.user.username[0], "tasks": tasks}
        return render(request, 'my_tasks_all.html', ctx)


class ToggleTask(View):
    def post(self, request):
        # Якщо користувач не авторизований — перенаправляємо на сторінку входу.
        if not request.user.is_authenticated:
            return redirect('signIn')

        # Визначаємо, чи є користувач адміністратором
        user = request.user
        is_admin = user_is_admin(user)

        # Отримуємо ID задачі з POST-запиту.
        task_id = request.POST.get('task_id')

        # URL, на який потрібно повернутися після виконання дії.
        next_url = request.POST.get('next', 'my_tasks_all')

        # Якщо задачі не існує — показуємо помилку і повертаємось назад.
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            messages.error(request, "Задачу не знайдено.")
            return redirect(next_url)

        # ДОСТУП:
        #  адмін: може змінювати будь-яку задачу
        #  співробітник: тільки якщо він виконавець цієї задачі
        if not is_admin and task.assigned_to != user:
            messages.error(
                request, "Ви можете змінювати тільки власні задачі.")
            return redirect(next_url)

        # перемикання статусу
        # Якщо статус == 'T', TO DO.
        # Якщо статус == 'O', DONE.
        if task.status == 'T':
            task.status = 'O'
        else:
            task.status = 'T'

        task.save()

        return redirect(next_url)


class SetTaskStatus(View):
    # Дозволені статуси задач.
    # T - To Do, D - Doing, I - In test, O - Done
    ALLOWED = {'T', 'D', 'I', 'O'}

    def post(self, request, id):
        # Перевірка авторизації: якщо користувач не увійшов — перенаправити на логін.
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        # Визначаємо, чи є користувач адміністратором.
        is_admin = user_is_admin(user)

        # Отримуємо новий статус із POST.
        status = request.POST.get('status') or request.POST.get('new_status')
        next_url = request.POST.get('next', 'my_tasks_all')

        # Перевірка: статус повинен бути одним із дозволених.
        if status not in self.ALLOWED:
            messages.error(request, "Invalid task status.")
            return redirect(next_url)

        # беремо task_id з POST, а якщо його немає – з URL (id)
        task_id = request.POST.get('task_id') or id

        # Пошук задачі в базі даних.
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            messages.error(request, "The task is not found.")
            return redirect(next_url)

        # ДОСТУП:
        # - адміністратор може змінювати будь-яку задачу
        # - звичайний співробітник — лише свою
        if not is_admin and task.assigned_to != user:
            messages.error(
                request, "You do not have permission to modify another employee's task.")
            return redirect(next_url)

        # Зберігаємо попередній статус (на випадок логування або перевірок).
        old_status = task.status
        task.status = status

        # Якщо статус змінено на "Doing" і робота над задачою ще не стартувала — встановлюємо час старту.
        if status == 'D' and task.start_time is None:
            from datetime import datetime
            task.start_time = datetime.now()
        # Якщо повертаємо задачу в "To Do" — скидаємо час старту, бо робота по суті ще не почалася.
        if status == 'T':
            task.start_time = None

        task.save()

        return redirect(next_url)
