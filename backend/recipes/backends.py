from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailAuthBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username
        if not email:
            return None

        try:
            user = User.objects.get(email=email)

            if user.check_password(password):
                return user
            else:
                return None
        except User.DoesNotExist:
            return None
