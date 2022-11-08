from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post, User

User = get_user_model()


class PostUrlsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текстовый пост',
            group=cls.group,
        )
        cls.templates = [
            {   # Проверка шаблонов для авторизованных пользователей
                '/': 'posts/index.html',
                '/group/test-slug/': 'posts/group_list.html',
                f'/profile/{cls.user.username}/': 'posts/profile.html',
                f'/posts/{cls.post.id}/': 'posts/post_detail.html',
                '/create/': 'posts/create_post.html',
                f'/posts/{cls.post.id}/edit/': 'posts/create_post.html'
            },
            {   # Доступ для авторизованных
                '/': HTTPStatus.OK,
                '/group/test-slug/': HTTPStatus.OK,
                f'/profile/{cls.user.username}/': HTTPStatus.OK,
                f'/posts/{cls.post.id}/': HTTPStatus.OK,
                '/create/': HTTPStatus.FOUND,
                '/unexisting_page/': HTTPStatus.NOT_FOUND,
                f'/posts/{cls.post.id}/edit/': HTTPStatus.FOUND
            },
            {   # Доступ для неавторизованных
                '/': HTTPStatus.OK,
                '/group/test-slug/': HTTPStatus.OK,
                f'/profile/{cls.user.username}/': HTTPStatus.OK,
                f'/posts/{cls.post.id}/': HTTPStatus.OK,
                '/create/': HTTPStatus.OK,
                '/unexisting_page/': HTTPStatus.NOT_FOUND,
                f'/posts/{cls.post.id}/edit/': HTTPStatus.OK,
            },
        ]

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.user_author = PostUrlsTest.user
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)

    def test_templates_for_authorized(self):
        """Проверка шаблонов для авторизованных пользователей"""
        for address, template in self.templates[0].items():
            with self.subTest(address=address):
                response = self.authorized_client_author.get(address)
                self.assertTemplateUsed(response, template)

    def test_edit_url_uses_correct_template(self):
        """Страница /posts/<post_id>/edit/ использует
        шаблон posts/post_create.html.
        """
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/',
            follow=True
        )
        self.assertRedirects(
            response, (f'/posts/{self.post.id}/')
        )

    def test_templates_for_everyone(self):
        """Проверка шаблонов для всех пользователей"""
        for address, template in self.templates[0].items():
            if address == f'/posts/{self.post.id}/':
                break
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_redirect_create(self):
        """Редирект неавторизованного"""
        response = self.guest_client.get('/create/', folow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_page_access_guest(self):
        """Доступ страниц неавторизованным"""
        for address, code in self.templates[1].items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, code)

    def test_page_access_autorized(self):
        """Доступ страниц авторизованным"""
        for address, code in self.templates[2].items():
            with self.subTest(address=address):
                response = self.authorized_client_author.get(address)
                self.assertEqual(response.status_code, code)
