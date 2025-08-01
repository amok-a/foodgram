from django.db import models
from django.contrib.auth.models import AbstractUser


NAME_MAX_LENGTH = 150


class User(AbstractUser):

    first_name = models.CharField(
        ("Имя"),
        max_length=NAME_MAX_LENGTH,
        blank=False,
        null=False,
        help_text=("Обязательное поле.")
    )
    last_name = models.CharField(
        ("Фамилия"),
        max_length=NAME_MAX_LENGTH,
        blank=False,
        null=False,
        help_text=("Обязательное поле.")
    )
    email = models.EmailField(
        ("Email"),
        unique=True,
        blank=False,
        null=False,
        help_text=("Обязательное поле. Укажите уникальный email-адрес.")
    )
    avatar = models.ImageField(
        ("Аватар"),
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text=("Загрузите изображение профиля.")
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    class Meta:
        verbose_name = ("Пользователь")
        verbose_name_plural = ("Пользователи")
        ordering = ["username"]

    def __str__(self):
        return self.username

    @property
    def recipe_count(self):
        return self.recipes.count()

    @property
    def subscriber_count(self):
        return self.following.count()

    @classmethod
    def create_user(cls, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)

        if not email:
            raise ValueError('The Email field must be set')
        email = cls.normalize_email(email)
        user = cls(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=cls._default_manager.db)
        return user

    @property
    def shopping_carts(self):
        return self.shopping_cart.all()

    @property
    def shopping_cart_count(self):
        return self.shopping_cart.count()
