import tracker.forms as forms
from . import common as views_common
import tracker.viewutil as viewutil

import settings

import django.contrib.auth.tokens
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
import django.contrib.auth as djauth
import django.contrib.auth.views as djauth_views
import django.utils.http
from django.views.decorators.csrf import csrf_protect,csrf_exempt,get_token as get_csrf_token
from django.core.urlresolvers import reverse
from django.shortcuts import render

__all__ = [
  'login',
  'logout',
  'password_reset',
  'password_reset_done',
  'password_reset_confirm',
  'password_reset_complete',
  'password_change',
  'password_change_done',
  'confirm_registration',
  ]
  
@never_cache
def login(request):
  message = None
  if 'next' in request.GET:
    message = 'Login required to continue.'
  return djauth_views.login(request, template_name='tracker/login.html', extra_context={'message': message})

@never_cache
def logout(request):
  djauth.logout(request)
  return django.shortcuts.redirect(request.META.get('HTTP_REFERER', settings.LOGOUT_REDIRECT_URL))

@never_cache
def password_reset(request):
  return djauth_views.password_reset(request,
    template_name='tracker/password_reset.html',
    email_template_name='password_reset_template',
    password_reset_form=forms.PostOfficePasswordResetForm,
    from_email=viewutil.get_default_email_from_user())

@never_cache
def password_reset_done(request):
  return views_common.tracker_response(request, 'tracker/password_reset_done.html')

@never_cache
def password_reset_confirm(request):
  uidb64 = request.GET['uidb64']
  token = request.GET['token']
  return djauth_views.password_reset_confirm(request,
    uidb64,
    token,
    template_name='tracker/password_reset_confirm.html')

@never_cache
def password_reset_complete(request):
  return views_common.tracker_response(request, 'tracker/password_reset_complete.html', {'login_url': reverse('login')})

@never_cache
@login_required
def password_change(request):
  return djauth_views.password_change(request, template_name='tracker/password_change.html')

@never_cache
@login_required
def password_change_done(request):
  return views_common.tracker_response(request, 'tracker/password_change_done.html')

@never_cache
def confirm_registration(request):
  AuthUser = djauth.get_user_model()
  uidb64 = request.GET.get('uidb64', None)
  uid = django.utils.http.urlsafe_base64_decode(uidb64) if uidb64 else None
  token = request.GET.get('token',None)
  user = None
  tokenGenerator = django.contrib.auth.tokens.default_token_generator
  try:
    user = AuthUser.objects.get(pk=uid)
  except:
    user = None
  if request.method == 'POST':
    form = forms.RegistrationConfirmationForm(user=user, token=token, token_generator=tokenGenerator, data=request.POST)
    if form.is_valid():
      form.save()
      return views_common.tracker_response(request, 'tracker/confirm_registration_done.html', {'user': form.user})
  else:
    form = forms.RegistrationConfirmationForm(user=user, token=token, token_generator=tokenGenerator, initial={'userid': uid, 'authtoken': token, 'username': user.username if user else ''})
  return views_common.tracker_response(request, 'tracker/confirm_registration.html', {'formuser': user, 'tokenmatches': tokenGenerator.check_token(user, token) if token else False, 'form': form})
