import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Group, Post, User

User = get_user_model()


class PostViewTest(TestCase):
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
        cls.html_list = [  # Проверка вызова соответствующего шаблона
            ("posts/index.html", reverse('posts:index')),
            ("posts/group_list.html", reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'})
             ),
            ("posts/create_post.html", reverse('posts:post_create')),
            ("posts/profile.html", reverse(
                'posts:profile', kwargs={'username': cls.user}
            )),
            ("posts/post_detail.html", reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.id}
            )),
            ("posts/create_post.html", reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.id}))
        ]
        cls.templates = [
            {   # Пагинатор
                reverse('posts:index'): 10,
                (reverse('posts:index') + '?page=2'): 3,
                (reverse('posts:group_list',
                         kwargs={"slug": 'test-slug'})): 10,
                (reverse('posts:group_list',
                         kwargs={"slug": 'test-slug'}) + '?page=2'): 3,
                (reverse('posts:profile',
                         kwargs={'username': cls.post.author})): 10,
                (reverse('posts:profile',
                         kwargs={'username': cls.post.author}) + '?page=2'): 3,
            },
        ]
        cls.list_test = (
            (   # Правильно ли выводится контекст
                reverse('posts:index'),
                reverse('posts:group_list',
                        kwargs={'slug': 'test-slug'}),
                reverse('posts:profile', kwargs={'username': cls.post.author}),
            ),
            (   # Шаблон сформирован с правильным полями формы
                reverse('posts:post_create'),
                reverse('posts:post_edit', kwargs={'post_id': cls.post.id})
            ),
        )
        cls.post_list = []
        for i in range(12):
            cls.post_list.append(Post(
                author=cls.user,
                text='Текстовый пост',
                group=cls.group,
            )
            )
        cls.obj = Post.objects.bulk_create(cls.post_list)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.user_author = PostViewTest.user
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)

    def test_post_where_needed(self):
        """Проверяет что пост отображается в
           index / group_list / profile"""
        post2 = Post.objects.create(author=self.user,
                                    text='Текстовый пост2',
                                    group=self.group
                                    )
        list_template = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': post2.group.slug}),
            reverse('posts:profile', kwargs={'username': post2.author})
        )
        for template in list_template:
            with self.subTest(template=template):
                response = self.authorized_client.get(template)
                first_objects = response.context['page_obj'][0]
                obj_text = first_objects.text
        self.assertEqual(obj_text, post2.text)

    def test_slug(self):
        """Тест что пост не попал в другую группу"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_objects = response.context['page_obj'][0]
        gorup_slug = first_objects.group.slug
        post2 = Post.objects.create(
            author=User.objects.create_user(username='saske'),
            text='Текстовый пост2',
            group=Group.objects.create(
                title='Тестовая группа2',
                slug='test-slug2',
                description='Тестовое описание2'
            ))
        self.assertNotEqual(gorup_slug, post2.group.slug)

    def test_right_templates(self):
        """Проверка вызова соответствующего шаблона"""
        for template, reverse_name in self.html_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_fist_page_in_template(self):
        """Пагинатор"""
        for reverse_name, count_page in self.templates[0].items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), count_page)

    def test_pages_show_correct_context(self):
        """Правильно ли выводится контекст"""
        for name_page in self.list_test[0]:
            with self.subTest(name_page=name_page):
                response = self.authorized_client.get(name_page)
                first_object = response.context['page_obj'][0]
                task_author_0 = first_object.author
                task_text_0 = first_object.text
                task_slug_0 = first_object.group.slug
                self.assertEqual(task_author_0, self.post.author)
                self.assertEqual(task_text_0, self.post.text)
                self.assertEqual(task_slug_0, self.group.slug)

    def test_post_detail_correct_context(self):
        """Контекст страницы post_detail корректен"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        first_object = response.context['post']
        task_author_0 = first_object.author
        task_text_0 = first_object.text
        task_slug_0 = self.group.slug
        self.assertEqual(task_author_0, self.post.author)
        self.assertEqual(task_text_0, self.post.text)
        self.assertEqual(task_slug_0, self.group.slug)

    def test_form_correct_context(self):
        """Шаблон сформирован с правильным полями формы"""
        for name_page in self.list_test[1]:
            with self.subTest(name_page=name_page):
                response = self.authorized_client_author.get(name_page)
                form_fields = {
                    'group': forms.fields.ChoiceField,
                    'text': forms.fields.CharField,
                }
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context['form'].fields[value]
                        self.assertIsInstance(form_field, expected)


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=User.objects.create_user(username='test_name'),
            text='Тестовая запись для поста',
            group=cls.group,
            image=uploaded
        )
        cls.image_list = (
            (
                reverse('posts:index'),
                reverse('posts:group_list',
                        kwargs={'slug': 'test-slug'}),
                reverse('posts:profile', kwargs={'username': cls.post.author}),
            ),
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='mob2556')
        self.user_follower = User.objects.create_user(username='Автор')
        self.user_not_follower = User.objects.create_user(
            username='НеПодписчик')

        self.authorized_client = Client()
        self.follower = Client()
        self.not_follower = Client()
        self.authorized_client.force_login(self.user)
        self.follower.force_login(self.user_follower)
        self.not_follower.force_login(self.user_not_follower)

    def test_cache(self):
        """Тестирование кэша"""
        before_editing = self.authorized_client.get(reverse('posts:index'))
        post_1 = Post.objects.get(text=self.post.text)
        post_1.text = 'Изменяем текст'
        post_1.save()
        after_editing = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(before_editing.content, after_editing.content)
        cache.clear()
        clearing_the_cache = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(before_editing.content, clearing_the_cache.content)

    def test_pages_show_correct_context(self):
        """Выводится ли картинка в контекст"""
        for name_page in self.image_list[0]:
            with self.subTest(name_page=name_page):
                response = self.authorized_client.get(name_page)
                first_object = response.context['page_obj'][0]
                task_author_0 = first_object.author
                task_text_0 = first_object.text
                task_slug_0 = first_object.group.slug
                task_image_0 = Post.objects.first().image
                self.assertEqual(task_author_0, self.post.author)
                self.assertEqual(task_text_0, self.post.text)
                self.assertEqual(task_slug_0, self.group.slug)
                self.assertEqual(task_image_0, 'posts/small.gif')

    def test_post_detail_correct_context(self):
        """Картинка выводиться в контекст post_detail"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        first_object = response.context['post']
        task_author_0 = first_object.author
        task_text_0 = first_object.text
        task_slug_0 = self.group.slug
        task_image_0 = Post.objects.first().image
        self.assertEqual(task_author_0, self.post.author)
        self.assertEqual(task_text_0, self.post.text)
        self.assertEqual(task_slug_0, self.group.slug)
        self.assertEqual(task_image_0, 'posts/small.gif')

    def test_authorized_can_follow(self):
        """Авторизованный пользователь может подписываться"""
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_follower.username}))
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_authorized_can_unfollow(self):
        """Не вторизованный пользователь не может подписываться"""
        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user_follower.username}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_context_follow(self):
        """ Подписанный пользователь видит записи"""
        Follow.objects.create(user=self.user_follower, author=self.user)
        Post.objects.create(
            author=self.user,
            text='Тестовая запись для подписчика'
        )
        response = self.follower.get(reverse('posts:follow_index'))
        first_object = response.context['page_obj'][0]
        first = first_object.text
        self.assertEqual(first, 'Тестовая запись для подписчика')
        response = self.not_follower.get(reverse('posts:follow_index'))
        self.assertNotContains(response, 'Тестовая запись для подписчика')

    def test_context_unfollow(self):
        """Не подписанный пользователь не видит записи"""
        Follow.objects.create(user=self.user_follower, author=self.user)
        Post.objects.create(
            author=self.user,
            text='Тестовая запись для подписчика'
        )
        response = self.not_follower.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        first = first_object.text
        self.assertEqual(first, 'Тестовая запись для подписчика')
        response = self.not_follower.get(reverse('posts:follow_index'))
        self.assertNotContains(response, 'Тестовая запись для подписчика')
