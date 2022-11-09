import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.forms import PostForm

from ..models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
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
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.user_author = PostFormTest.user
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)

    def test_new_entry_in_the_database(self):
        """Проверка, что создается новая запись"""
        post_count = Post.objects.count()
        form_data = {
            "title": 'New',
            "text": 'Текстовый пост',
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': self.user_author.username}))
        self.assertEqual(Post.objects.count(), post_count + 1)

    def test_edited(self):
        """Проверка, что редактируется запись"""
        form_data = {
            "text": 'Текстовый пост1',
            "slug": self.post.group.slug

        }
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': self.post.id}))
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text']
            ).exists())

    def test_add_image(self):
        """Проверка что картинка добавилась"""
        test_count = Post.objects.count()
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
        form_data = {
            'group': self.group.id,
            'text': 'Пост с картинкой',
            'image': uploaded,
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post_1 = Post.objects.get(text=form_data['text'])
        self.assertEqual(Post.objects.count(), test_count + 1)
        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': self.user_author.username}))
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=self.group.id,
            ).exists()
        )
        self.assertEqual(post_1.text, form_data['text'])

    def test_comment_authorized(self):
        """Авторизованый может оставить комментарий"""
        form_data = {
            'text': 'n1ce',
            'author': self.user
        }
        response = self.authorized_client_author.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True)
        first = response.context['comment']
        find_comment = first.text
        self.assertContains(response, form_data['text'])
        self.assertEqual(find_comment, form_data['text'])

    def test_comment_authorized(self):
        """Не авторизованный не может оставить комментарий"""
        form_data = {
            'text': 'n1ce',
            'author': self.user
        }
        response = self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True)
        self.assertNotContains(response, form_data['text'])
