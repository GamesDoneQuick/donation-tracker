import post_office.mail
import post_office.models
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from tracker import settings

from . import mailutil


def default_registration_template_name():
    return getattr(
        settings, 'REGISTER_EMAIL_TEMPLATE_NAME', 'default_registration_template'
    )


def default_registration_template():
    return post_office.models.EmailTemplate.objects.get_or_create(
        name=default_registration_template_name(),
        defaults=dict(
            subject='Account Registration',
            description="""Email template for user account registration.

The following context variables are defined:
user -- the User object
domain -- the web-domain of the website
confirmation_url -- the full URL (including token) the user should visit to confirm their registration and set their password
""",
            html_content="""Hello {{ user }},
    <p>
    You (or something pretending to be you) has requested an account on {{ domain }}. Please follow this <a href="{{ confirmation_url }}">link</a> to complete registering your account.
    </p>

    - The Staff
""".strip(),
        ),
    )[0]


def default_volunteer_registration_template_name():
    return getattr(
        settings,
        'VOLUNTEER_REGISTRATION_TEMPLATE_NAME',
        'default_volunteer_registration_template',
    )


def default_volunteer_registration_template():
    return post_office.models.EmailTemplate.objects.get_or_create(
        name=default_volunteer_registration_template_name(),
        defaults=dict(
            subject='Donation Processing',
            description="""Email template for donation volunteers.

The following context variables are defined:
user -- the User object
event -- the Event that this email is being send for
is_host -- True if the user was imported as a host
is_head -- True if the user was imported as a head donation screener
is_schedule -- True if the user was imported as a schedule viewer
confirmation_url -- the full URL (including token) the user should visit to confirm their registration and set their password
password_reset_url -- the full URL the user should visit if the above link expires (happens after 3 days if using default Django settings)
admin_url -- the full URL of the admin site (which will redirect them to login if need be)
""".strip(),
            content="""
Hello {{ user }},

{% if is_head %}
You are receiving this e-mail because you have been listed as a head donation processor during {{ event.name }}.
{% elif is_host %}
You are receiving this e-mail because you have been listed as a host during {{ event.name }}.
{% elif is_schedule %}
You are receiving this e-mail because you have been listed as a schedule viewer during {{ event.name }}.
{% else %}
You are receiving this e-mail because you have been listed as a donation processor during {{ event.name }}.
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
{% elif is_schedule %}
You are receiving this e-mail because you have been listed as a schedule viewer during {{ event.name }}.
{% else %}
You are receiving this e-mail because you have been listed as a donation processor during {{ event.name }}.
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
        ),
    )[0]


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
    sender = sender or settings.DEFAULT_FROM_EMAIL
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
    password_reset_url = request.build_absolute_uri(
        reverse('tracker:password_reset'),
    )

    def reset_url():
        raise AssertionError('reset_url is deprecated, use confirmation_url instead')

    return post_office.mail.send(
        recipients=[user.email],
        sender=sender,
        template=template,
        context={
            **extra_context,
            'user': user,
            'domain': get_current_site(request).domain,
            'confirmation_url': confirmation_url,
            'reset_url': reset_url,
            'password_reset_url': password_reset_url,
        },
    )
