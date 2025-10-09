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
from django.urls import reverse


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
            response = JsonResponse({"error": "Invalid User"})
            response.status_code = 403
            return response

        user = request.user

        type = request.POST['type']
        if type == 'edit_status':
            task_id = request.POST['task_id']
            status = request.POST['board_id']

            task = Task.objects.filter(id=task_id).first()

            if status in ['O', 'B', 'L'] or task.status in ['O', 'B', 'L']:
                if user == task.project.owner:
                    task.status = status
                    task.save()

                else:
                    response = JsonResponse(
                        {"error": "You Do Not Have Permission"})
                    response.status_code = 403
                    return response
            else:
                if user == task.assigned_to or user == task.project.owner:
                    task.status = status
                    if status == 'D':
                        task.start_time = datetime.datetime.today().date()
                    task.save()
                else:
                    response = JsonResponse(
                        {"error": "You Do Not Have Permission"})
                    response.status_code = 403
                    return response

            response = JsonResponse({"message": "OK"})
            response.status_code = 200
            return response

        if type == 'edit_end_time':

            task_id = request.POST['task_id']
            end_time = request.POST['new_end_time']

            task = Task.objects.filter(id=task_id).first()

            if user == task.project.owner:
                task.end_time = end_time
                task.save()

                response = JsonResponse({"message": "OK"})
                response.status_code = 200
                return response

            else:
                response = JsonResponse(
                    {"error": "You Do Not Have Permission"})
                response.status_code = 403
                return response
            
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
    """Перемикання статусу задачі з чекбокса (між To Do 'T' і Done 'O')."""
    def post(self, request, id):
        if not request.user.is_authenticated:
            return redirect('signIn')

        task = Task.objects.select_related('project').filter(id=id).first()
        if not task:
            return redirect('my_tasks_all')

        # дозволяємо змінювати лише виконавцю або власнику проєкту
        if task.assigned_to != request.user and task.project.owner != request.user:
            return redirect('my_tasks_all')

        done_checked = (request.POST.get('done') == 'on')
        task.status = 'O' if done_checked else 'T'
        task.save()

        # повертаємось туди, звідки прийшли (якщо передали), або на my_tasks_all
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('my_tasks_all')
class SetTaskStatus(View):
    """
    Change task status from the My Tasks page.

    Accepts either:
      - checkbox 'done' (on/off)  -> sets 'O' or 'T'
      - select 'new_status' in {'T','D','I','O'}

    Only the assignee OR the project owner may change it.
    """
    ALLOWED = {'T', 'D', 'I', 'O'}  # To Do, Doing, In Test, Done

    def post(self, request, id):
        if not request.user.is_authenticated:
            return redirect('signIn')

        task = Task.objects.select_related('project', 'assigned_to').filter(id=id).first()
        if not task:
            return redirect('my_tasks_all')

        if task.assigned_to != request.user and task.project.owner != request.user:
            return redirect('my_tasks_all')

        # 1) handle checkbox "done"
        if request.POST.get('done') is not None:
            done_checked = (request.POST.get('done') == 'on')
            new_status = 'O' if done_checked else 'T'
        else:
            # 2) handle dropdown "new_status"
            new_status = request.POST.get('new_status', '').strip()

        if new_status not in self.ALLOWED:
            return redirect('my_tasks_all')

        # convenience: set/clear start_time when moving to Doing/To Do
        if new_status == 'D' and not task.start_time:
            task.start_time = datetime.date.today()
        if new_status == 'T':
            task.start_time = None

        task.status = new_status
        task.save()

        return redirect(request.POST.get('next') or 'my_tasks_all')