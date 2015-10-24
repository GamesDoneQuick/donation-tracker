import django.contrib.auth as auth
import django.contrib.auth.models as auth_models

# Future proofing against replacing auth model
AuthUser = auth.get_user_model()


class EmailLoginAuthBackend:
    """Custom authentication backend which supports 
    e-mail as identity. Note that if more than one user has
    the same e-mail, they will all not be able to use that 
    email and must use the user id instead"""

    supports_inactive_user = False

    def authenticate(self, username=None, password=None, email=None):
        AUTH_METHODS = [
            {'email': username},
            {'email': email},
        ]

        try:
            userFilter = AuthUser.objects.none()
            for method in AUTH_METHODS:
                userFilter = AuthUser.objects.filter(**method)
                if userFilter.count() == 1:
                    user = userFilter[0]
                    if user.check_password(password):
                        return user
        except Exception as e:
            pass
        return None

    def get_user(self, user_id):
        try:
            return AuthUser.objects.get(pk=user_id)
        except AuthUser.DoesNotExist:
            return None
