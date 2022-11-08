from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, User

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текстовый пост, который проверяет символы',
        )
        cls.models_spec = [
            {
                "text": 'Введите текст поста',  # Тест help_text
                "group": 'Группа, к которой будет относиться пост',
            },
            {
                "text": 'Текст поста',  # Тест verbose_name
                "pub_date": 'Дата публикации',
                "author": 'Автор',
                "group": 'Группа',
            },
        ]

    def test_models_have_correct_object_names(self):
        """для класса Group — название группы"""
        task = PostModelTest.group
        expected_object = task.title
        self.assertEqual(expected_object, str(task))

    def test_post_text(self):
        """Post — первые пятнадцать символов поста: **post.text[:15]"""
        task = self.post.text
        expected_object = task[:15]
        self.assertNotEqual(expected_object, str(task))

    def test_help_text(self):
        """Тест help_text"""
        task = PostModelTest.post
        for value, expected in self.models_spec[0].items():
            with self.subTest(value=value):
                self.assertEqual(
                    task._meta.get_field(value).help_text, expected)

    def test_verbose_name(self):
        """ Тестирование verbose_name """
        task = PostModelTest.post
        for value, expected in self.models_spec[1].items():
            with self.subTest(value=value):
                self.assertEqual(
                    task._meta.get_field(value).verbose_name, expected)
