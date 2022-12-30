import post_office.mail
import post_office.models
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from . import viewutil, mailutil


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
""".strip(),
    )


def default_volunteer_registration_template_name():
    return getattr(
        settings,
        'VOLUNTEER_REGISTRATION_TEMPLATE_NAME',
        'default_volunteer_registration_template',
    )


def default_volunteer_registration_template():
    return post_office.models.EmailTemplate(
        name=default_volunteer_registration_template_name(),
        subject='Donation Processing',
        description="""Email template for donation volunteers.

The following context variables are defined:
user -- the User object
event -- the Event that this email is being send for
is_host -- True if the user was imported as a host
is_head -- True if the user was importes as a head donation screener
confirmation_url -- the full URL (including token) the user should visit to confirm their registration and set their password
reset_url -- deprecated name for confirmation_url
password_reset_url -- the full URL the user should visit if the above link expires (happens after 3 days if using default Django settings)
admin_url -- the full URL of the admin site (which will redirect them to login if need be)
""".strip(),
        content="""
Hello {{ user }},

{% if is_head %}
You are receiving this e-mail because you have been listed as a head donation processor during {{ event.name }}.
{% elif is_host %}
You are receiving this e-mail because you have been listed as a host during {{ event.name }}.
{% else %}
You are receiving this e-mail because you have been listed as a donation processer during {{ event.name }}.
{% endif %}

{% if user.is_active %}
You seem to already have an active account on the donation tracker. If so, no further action is required on your part at this time. If you have forgotten your password, you may re-set it by entering your e-mail at: {{ password_reset_url }}
{% else %}
You have been registered for an account on the donation tracker. You will be required to log into this account during all of your shifts. To activate your account and set your password, you have been provided with a temporary URL below to confirm your account and select a username and password.

Confirm your account: {{ confirmation_url }}

The above link will expire after a certain period, and if that time has elapsed, please request a password reset password reset with the following email address: {{ user.email }}

{{ password_reset_url }}
{% endif %}

Once you're finished with that, you may log in to the admin site at the url below. Please note that the username and password are both CaSe SeNsItIvE.

{{ admin_url }}

- The Staff
""".strip(),
        html_content="""
Hello {{ user }},

<p>
{% if is_head %}
You are receiving this e-mail because you have been listed as a head donation processor during {{ event.name }}.
{% elif is_host %}
You are receiving this e-mail because you have been listed as a host during {{ event.name }}.
{% else %}
You are receiving this e-mail because you have been listed as a donation processer during {{ event.name }}.
{% endif %}
</p>

{% if user.is_active %}
<p>
You seem to already have an active account on the donation tracker. If so, no further action is required on your part at this time. If you have forgotten your password, you may re-set it by entering your e-mail on this page (<a href="{{ password_reset_url }}">{{ password_reset_url }}</a>).
</p>
{% else %}
<p>
You have been registered for an account on the donation tracker. You will be required to log into this account during all of your shifts. To activate your account and set your password, you have been provided with a temporary URL below to confirm your account and select a username and password.
</p>

<p>
Confirm your account: <a href="{{ confirmation_url }}">{{ confirmation_url }}</a>
</p>

<p>
The above link will expire after a certain period, and if that time has elapsed, please request a <a href="{{ password_reset_url }}">password reset</a> with the following email address: <tt>{{ user.email }}</tt>.
</p>
{% endif %}

<p>
Once you're finished with that, you may <a href="{{ admin_url }}">log in to the admin site</a>. Please note that the username and password are both CaSe SeNsItIvE.
</p>

- The Staff
""".strip(),
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
    sender = sender or viewutil.get_default_email_from_user()
    extra_context = extra_context or {}
    confirmation_url = request.build_absolute_uri(
        reverse(
            'tracker:confirm_registration',
            kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': token_generator.make_token(user),
            },
        )
    )
    password_reset_url = request.build_absolute_uri(reverse('tracker:password_reset'),)
    return post_office.mail.send(
        recipients=[user.email],
        sender=sender,
        template=template,
        context={
            **extra_context,
            'user': user,
            'confirmation_url': confirmation_url,
            'reset_url': confirmation_url,  # reset_url is deprecated
            'password_reset_url': password_reset_url,
        },
    )
