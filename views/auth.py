import django.contrib.auth.tokens
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
import django.contrib.auth as djauth
import django.contrib.auth.views as djauth_views
import django.utils.http
from django.views.decorators.csrf import csrf_protect, csrf_exempt, get_token as get_csrf_token
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.template import Context
from django.utils.six.moves.urllib.parse import urlparse

import settings

import tracker.forms as forms
from . import common as views_common
import tracker.viewutil as viewutil
import tracker.auth

__all__ = [
    'login',
    'logout',
    'password_reset',
    'password_reset_done',
    'password_reset_confirm',
    'password_reset_complete',
    'password_change',
    'password_change_done',
    'register',
    'confirm_registration',
]


@never_cache
def login(request):
    message = None
    next = None
    next = request.POST.get('next', request.GET.get('next', None))

    if next != None:
        nextUrl = urlparse(next)
        # TODO: this probably belongs in a user-configurable table somwhere
        if nextUrl.path.startswith('/user/submit_prize'):
            message = 'In order to submit a prize, you will need to log in or register an account. This will allow you to view and manage your prize data later on our site.'
        else:
            message = 'Login required to continue.'

    # Don't post a login page if the user is already logged in!
    if request.user.is_authenticated():
        return HttpResponseRedirect(next if next else settings.LOGIN_REDIRECT_URL)

    def delegate_login_render(request, template, context=None, status=200):
        return djauth_views.login(request, template_name=template, extra_context=context, redirect_field_name='next')

    return views_common.tracker_response(request, template='tracker/login.html', qdict={'message': message}, delegate=delegate_login_render)


@never_cache
def logout(request):
    djauth.logout(request)
    return django.shortcuts.redirect(settings.LOGOUT_REDIRECT_URL)


@never_cache
def password_reset(request):
    def delegate_password_reset_render(request, template, context=None, status=200):
        return djauth_views.password_reset(request,
                                           template_name=template,
                                           email_template_name=tracker.auth.default_password_reset_template(),
                                           password_reset_form=forms.PostOfficePasswordResetForm,
                                           from_email=viewutil.get_default_email_from_user(),
                                           extra_context=context)

    return views_common.tracker_response(request, template='tracker/password_reset.html', delegate=delegate_password_reset_render)


@never_cache
def password_reset_done(request):
    return views_common.tracker_response(request, 'tracker/password_reset_done.html')


@never_cache
def password_reset_confirm(request):
    uidb64 = request.GET['uidb64']
    token = request.GET['token']

    def delegate_password_reset_confirm_render(request, template, context=None, status=200):
        return djauth_views.password_reset_confirm(
            request,
            uidb64,
            token,
            template_name=template,
            extra_context=context)

    return views_common.tracker_response(request, template='tracker/password_reset_confirm.html', delegate=delegate_password_reset_confirm_render)


@never_cache
def password_reset_complete(request):
    return views_common.tracker_response(request, 'tracker/password_reset_complete.html', {'login_url': reverse('login')})


@never_cache
@login_required
def password_change(request):
    def delegate_password_change_render(request, template, context=None, status=200):
        return djauth_views.password_change(
            request,
            template_name=template,
            extra_context=context)

    return views_common.tracker_response(request, 'tracker/password_change.html', delegate=delegate_password_change_render)


@never_cache
@login_required
def password_change_done(request):
    return views_common.tracker_response(request, 'tracker/password_change_done.html')


@never_cache
def register(request):
    if request.method == 'POST':
        form = forms.RegistrationForm(data=request.POST)
        if form.is_valid():
            form.save(
                email_template=tracker.auth.default_registration_template(), request=request)
            return views_common.tracker_response(request, 'tracker/register_done.html')
    else:
        form = forms.RegistrationForm()

    return views_common.tracker_response(request, "tracker/register.html", {'form': form})


@never_cache
def confirm_registration(request):
    AuthUser = djauth.get_user_model()
    uidb64 = request.GET.get('uidb64', None)
    uid = django.utils.http.urlsafe_base64_decode(uidb64) if uidb64 else None
    token = request.GET.get('token', None)
    user = None
    tokenGenerator = django.contrib.auth.tokens.default_token_generator
    try:
        user = AuthUser.objects.get(pk=uid)
    except:
        user = None
    if request.method == 'POST':
        form = forms.RegistrationConfirmationForm(
            user=user, token=token, token_generator=tokenGenerator, data=request.POST)
        if form.is_valid():
            form.save()
            return views_common.tracker_response(request, 'tracker/confirm_registration_done.html', {'user': form.user})
    else:
        form = forms.RegistrationConfirmationForm(user=user, token=token, token_generator=tokenGenerator, initial={
                                                  'userid': uid, 'authtoken': token, 'username': user.username if user else ''})
    return views_common.tracker_response(request, 'tracker/confirm_registration.html', {'formuser': user, 'tokenmatches': tokenGenerator.check_token(user, token) if token else False, 'form': form})
