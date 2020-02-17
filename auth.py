import post_office.mail
import post_office.models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.safestring import mark_safe

from . import viewutil, mailutil

# Future proofing against replacing auth model
AuthUser = get_user_model()


class EmailLoginAuthBackend:
    """Custom authentication backend which supports
    e-mail as identity. Note that if more than one user has
    the same e-mail, they will all not be able to use that
    email and must use the user id instead"""

    supports_inactive_user = False

    def authenticate(self, request=None, username=None, password=None, email=None):
        auth_methods = [
            {'email': username},
            {'email': email},
        ]

        try:
            user_filter = AuthUser.objects.none()
            for method in auth_methods:
                user_filter = AuthUser.objects.filter(**method)
                if user_filter.count() == 1:
                    user = user_filter[0]
                    if user.check_password(password):
                        return user
        except Exception:
            pass
        return None

    def get_user(self, user_id):
        try:
            return AuthUser.objects.get(pk=user_id)
        except AuthUser.DoesNotExist:
            return None


def default_password_reset_template_name():
    return getattr(
        settings,
        'PASSWORD_RESET_EMAIL_TEMPLATE_NAME',
        'default_password_reset_template',
    )


# TODO: get better control over when the auth links expire, and explicitly state the expiration time
def default_password_reset_template():
    return post_office.models.EmailTemplate(
        name=default_password_reset_template_name(),
        subject='Password Reset',
        description="""Email template for user password reset.

The following context variables are defined:
user -- the User object
domain -- the web-domain of the website
reset_url -- the token-encoded url to redirect the user to
""",
        html_content="""Hello {{ user }},
    <p>
    You (or something pretending to be you) has requested a password reset for your account on {{ domain }}. Please follow this <a href="{{ reset_url }}">link</a> to reset your password.
    </p>

    <p>
    This login link will expire after you reset your password.
    </p>

    - The Staff
""",
    )


def default_registration_template_name():
    return getattr(
        settings, 'REGISTER_EMAIL_TEMPLATE_NAME', 'default_registration_template'
    )


def default_registration_template():
    return post_office.models.EmailTemplate(
        name=default_registration_template_name(),
        subject='Account Registration',
        description="""Email template for user account registration.

The following context variables are defined:
user -- the User object
domain -- the web-domain of the website
reset_url -- the token-encoded url to redirect the user to
""",
        html_content="""Hello {{ user }},
    <p>
    You (or something pretending to be you) has requested an account on {{ domain }}. Please follow this <a href="{{ reset_url }}">link</a> to complete registering your account.
    </p>

    - The GamesDoneQuick Staff
""",
    )


def send_registration_mail(
    request,
    user,
    template=None,
    sender=None,
    token_generator=default_token_generator,
    extra_context=None,
):
    template = template or mailutil.get_email_template(
        default_registration_template_name(), default_registration_template()
    )
    return send_auth_token_mail(
        user,
        request.get_host(),
        request.build_absolute_uri(
            reverse(
                'tracker:confirm_registration',
                kwargs={
                    'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': token_generator.make_token(user),
                },
            )
        ),
        template,
        sender,
        extra_context,
    )


def send_auth_token_mail(
    user, domain, confirm_url, template, sender=None, extra_context=None,
):
    if not sender:
        sender = viewutil.get_default_email_from_user()
    format_context = {
        'domain': domain,
        'user': user,
        'reset_url': mark_safe(confirm_url),
    }
    if extra_context:
        format_context.update(extra_context)
    return post_office.mail.send(
        recipients=[user.email],
        sender=sender,
        template=template,
        context=format_context,
    )
