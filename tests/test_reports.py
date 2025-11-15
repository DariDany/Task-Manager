from django.test import TestCase, Client
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from datetime import datetime

from reports.models import ProjectInfo, UserInfo, UserInProject
from reports.views import Report
from task_manager.models import Project


class ReportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Створюємо тестові проекти
        self.project1 = Project.objects.create(
            name='Test Project 1',
            description='Test Description 1',
            owner=self.user,
            members='[]',
            profile_photo='/media/project-logos/1.png'
        )

        self.project2 = Project.objects.create(
            name='Test Project 2',
            description='Test Description 2',
            owner=self.user,
            members='[2, 3]',  # Інші користувачі
            profile_photo='/media/project-logos/2.png'
        )

    def test_report_get_unauthenticated_redirects_to_signin(self):
        """Тест що неаутентифікований користувач редіректиться на сторінку входу"""
        response = self.client.get('/report/')
        self.assertRedirects(response, '/signIn')

    def test_report_get_authenticated_returns_report_page(self):
        """Тест що аутентифікований користувач отримує сторінку звіту"""
        self.client.force_login(self.user)
        response = self.client.get('/report/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report.html')

    def test_report_get_context_data(self):
        """Тест що контекст містить всі необхідні дані"""
        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        self.assertIn('user', context)
        self.assertIn('first', context)
        self.assertIn('p_info', context)
        self.assertIn('u_info', context)
        self.assertIn('u_in_p', context)
        self.assertIn('time', context)

        self.assertEqual(context['user'], self.user)
        self.assertEqual(context['first'], 't')  # Перша літера username

    def test_report_get_only_user_projects(self):
        """Тест що відображаються тільки проекти користувача"""
        # Створюємо проект, який не належить користувачу
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        other_project = Project.objects.create(
            name='Other Project',
            description='Other Description',
            owner=other_user,
            members='[]',
            profile_photo='/media/project-logos/3.png'
        )

        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        p_info_list = context['p_info']

        # Перевіряємо що тільки проекти користувача включені в звіт
        project_names = [p_info.project.name for p_info in p_info_list]
        self.assertIn('Test Project 1', project_names)
        self.assertIn('Test Project 2', project_names)
        self.assertNotIn('Other Project', project_names)

    def test_report_get_project_info_objects(self):
        """Тест що створюються коректні об'єкти ProjectInfo"""
        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        p_info_list = context['p_info']

        # Перевіряємо що всі елементи є об'єктами ProjectInfo
        for p_info in p_info_list:
            self.assertIsInstance(p_info, ProjectInfo)

        # Перевіряємо кількість проектів
        self.assertEqual(len(p_info_list), 2)

    def test_report_get_user_info_object(self):
        """Тест що створюється коректний об'єкт UserInfo"""
        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        u_info = context['u_info']

        self.assertIsInstance(u_info, UserInfo)
        self.assertEqual(u_info.user, self.user)

    def test_report_get_user_in_projects_objects(self):
        """Тест що створюються коректні об'єкти UserInProject"""
        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        u_in_p_list = context['u_in_p']

        # Перевіряємо що всі елементи є об'єктами UserInProject
        for u_in_p in u_in_p_list:
            self.assertIsInstance(u_in_p, UserInProject)

        # Перевіряємо кількість (має бути 2 проекти)
        self.assertEqual(len(u_in_p_list), 2)

    def test_report_get_time_in_context(self):
        """Тест що час коректно додається до контексту"""
        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        time = context['time']

        self.assertIsInstance(time, datetime)

    def test_report_get_user_as_project_member(self):
        """Тест що користувач бачить проекти де він є членом"""
        # Створюємо проект де користувач є членом, але не власником
        other_user = User.objects.create_user(
            username='owneruser',
            password='ownerpass123'
        )
        member_project = Project.objects.create(
            name='Member Project',
            description='Member Description',
            owner=other_user,
            members=f'[{self.user.id}]',  # Поточний користувач є членом
            profile_photo='/media/project-logos/4.png'
        )

        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        p_info_list = context['p_info']

        # Перевіряємо що проект члена включений в звіт
        project_names = [p_info.project.name for p_info in p_info_list]
        self.assertIn('Member Project', project_names)

    def test_report_get_excludes_non_member_projects(self):
        """Тест що проекти де користувач не є членом виключаються"""
        # Створюємо проект де користувач не є ні власником, ні членом
        other_user1 = User.objects.create_user(
            username='owner1',
            password='pass123'
        )
        other_user2 = User.objects.create_user(
            username='member1',
            password='pass123'
        )
        non_member_project = Project.objects.create(
            name='Non Member Project',
            description='Non Member Description',
            owner=other_user1,
            members=f'[{other_user2.id}]',  # Інший користувач є членом
            profile_photo='/media/project-logos/5.png'
        )

        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        p_info_list = context['p_info']

        # Перевіряємо що проект не включений в звіт
        project_names = [p_info.project.name for p_info in p_info_list]
        self.assertNotIn('Non Member Project', project_names)

    def test_report_get_empty_projects(self):
        """Тест обробки ситуації коли у користувача немає проектів"""
        # Видаляємо всі проекти
        Project.objects.all().delete()

        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context
        p_info_list = context['p_info']
        u_in_p_list = context['u_in_p']

        # Перевіряємо що списки порожні
        self.assertEqual(len(p_info_list), 0)
        self.assertEqual(len(u_in_p_list), 0)

        # Перевіряємо що сторінка все одно завантажується
        self.assertEqual(response.status_code, 200)

    def test_report_get_context_structure(self):
        """Тест структури контекстних даних"""
        self.client.force_login(self.user)
        response = self.client.get('/report/')

        context = response.context

        # Перевіряємо типи даних в контексті
        self.assertIsInstance(context['p_info'], list)
        self.assertIsInstance(context['u_in_p'], list)
        self.assertIsInstance(context['u_info'], UserInfo)
        self.assertIsInstance(context['time'], datetime)

        # Перевіряємо що перша літера імені користувача коректна
        self.assertEqual(context['first'], self.user.username[0])
