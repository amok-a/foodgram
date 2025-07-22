from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailAuthBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username
        logger.debug(f"EmailAuthBackend: Попытка аутентификации с email: {email}")

        if not email:
            logger.error("EmailAuthBackend: Email не указан.")
            return None

        try:
            user = User.objects.get(email=email)
            logger.debug(f"EmailAuthBackend: Пользователь найден с email: {email}")
            logger.debug(f"EmailAuthBackend: Хеш пароля из базы данных: {user.password}")
            logger.debug(f"EmailAuthBackend: Переданный пароль: {'*' * len(password)}")

            if user.check_password(password):
                logger.debug(f"EmailAuthBackend: Пароль совпадает для пользователя: {email}")
                return user
            else:
                logger.debug(f"EmailAuthBackend: Пароль НЕ совпадает для пользователя: {email}")
                return None
        except User.DoesNotExist:
            logger.debug(f"EmailAuthBackend: Пользователь с email {email} не существует.")
            return None
        except Exception as e:
            logger.exception(f"EmailAuthBackend: Произошла непредвиденная ошибка: {e}")
            return None