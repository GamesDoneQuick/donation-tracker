import django.contrib.auth as djauth
import django.contrib.auth.tokens
import django.utils.http
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.cache import never_cache

import tracker.auth
import tracker.forms as forms
from . import common as views_common

__all__ = [
    'register',
    'confirm_registration',
]


@never_cache
def register(request):
    if request.method == 'POST':
        form = forms.RegistrationForm(data=request.POST)
        if form.is_valid():
            form.save(
                email_template=tracker.auth.default_registration_template(),
                request=request,
            )
            return views_common.tracker_response(request, 'tracker/register_done.html')
    else:
        form = forms.RegistrationForm()

    return views_common.tracker_response(
        request, 'tracker/register.html', {'form': form}
    )


INTERNAL_REGISTRATION_URL_TOKEN = 'register-user'
INTERNAL_REGISTRATION_SESSION_TOKEN_KEY = '_register_user_token'


@never_cache
def confirm_registration(request, uidb64, token):
    AuthUser = djauth.get_user_model()  # noqa
    uid = django.utils.http.urlsafe_base64_decode(uidb64)
    try:
        user = AuthUser.objects.get(pk=uid)
        if user.is_active:  # this is only for new users
            raise PermissionDenied
    except AuthUser.DoesNotExist:
        raise PermissionDenied
    token_generator = django.contrib.auth.tokens.default_token_generator

    if token == INTERNAL_REGISTRATION_URL_TOKEN:
        session_token = request.session.get(INTERNAL_REGISTRATION_SESSION_TOKEN_KEY)
        if token_generator.check_token(user, session_token):
            if request.method == 'POST':
                form = forms.RegistrationConfirmationForm(
                    user=user,
                    token=session_token,
                    token_generator=token_generator,
                    data=request.POST,
                )
                if form.is_valid():
                    form.save()
                    return views_common.tracker_response(
                        request,
                        'tracker/confirm_registration_done.html',
                        {'user': form.user},
                    )
            else:
                form = forms.RegistrationConfirmationForm(
                    user=user,
                    token=session_token,
                    token_generator=token_generator,
                    initial={
                        'userid': uid,
                        'username': user.username,
                    },
                )
            return views_common.tracker_response(
                request,
                'tracker/confirm_registration.html',
                {
                    'formuser': user,
                    'form': form,
                },
            )
    else:
        if token_generator.check_token(user, token):
            request.session[INTERNAL_REGISTRATION_SESSION_TOKEN_KEY] = token
            return HttpResponseRedirect(
                reverse(
                    'tracker:confirm_registration',
                    kwargs={'uidb64': uidb64, 'token': INTERNAL_REGISTRATION_URL_TOKEN},
                )
            )

    raise PermissionDenied
