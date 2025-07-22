from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):

    first_name = models.CharField(
        ("Имя"),
        max_length=150,
        blank=False,
        null=False,
        help_text=("Обязательное поле.")
    )
    last_name = models.CharField(
        ("Фамилия"),
        max_length=150,
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
        default="avatars/default_avatar.png",
        blank=True,
        null=True,
        help_text=("Загрузите изображение профиля.")
    )

    class Meta:
        verbose_name = ("Пользователь")
        verbose_name_plural = ("Пользователи")
        ordering = ["username"]

    def __str__(self):
        return self.username

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
