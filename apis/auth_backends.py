from django.contrib.auth.backends import BaseBackend
from .models import User

class MatricOrEmailBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            if '@' in username:
                # Case-insensitive email lookup
                user = User.objects.get(email__iexact=username)
            else:
                # Case-insensitive matric number lookup
                user = User.objects.get(matric_number__iexact=username)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
